"""Move the old exe into backup_gitea and the new exe into the old file name."""

import os
import time
from datetime import datetime
from pathlib import Path

from gitea_updater.constants import BACKUP_DIR_NAME, BACKUP_TIMESTAMP_FORMAT
from gitea_updater.errors import UpdateError

_RETRY_INTERVAL_SECONDS = 0.5


def backup_path_for(exe: Path, now: datetime) -> Path:
    """`backup_gitea/<name>`; on collision add a timestamp, then a counter."""
    backup_dir = exe.parent / BACKUP_DIR_NAME
    candidate = backup_dir / exe.name
    if not candidate.exists():
        return candidate
    stem = f"{exe.stem}-{now.strftime(BACKUP_TIMESTAMP_FORMAT)}"
    candidate = backup_dir / f"{stem}{exe.suffix}"
    counter = 2
    while candidate.exists():
        candidate = backup_dir / f"{stem}-{counter}{exe.suffix}"
        counter += 1
    return candidate


class ExeSwapper:
    """File moves for the swap; retries while Windows still holds the exe locked."""

    def __init__(self, unlock_timeout_seconds: float) -> None:
        self._unlock_timeout = unlock_timeout_seconds

    def swap(self, exe: Path, new_file: Path) -> Path:
        """Return the backup path. On failure the old exe is back in place."""
        backup = backup_path_for(exe, datetime.now())
        backup.parent.mkdir(exist_ok=True)
        self._move(exe, backup)
        try:
            self._move(new_file, exe)
        except UpdateError:
            self._move(backup, exe)
            raise
        return backup

    def rollback(self, exe: Path, backup: Path) -> None:
        """Put the backup back under the exe name, replacing the new exe."""
        self._move(backup, exe)

    def _move(self, source: Path, target: Path) -> None:
        deadline = time.monotonic() + self._unlock_timeout
        while True:
            try:
                os.replace(source, target)
                return
            except FileNotFoundError as error:
                raise UpdateError(f"Cannot move {source} -> {target}: {error}") from error
            except PermissionError as error:
                # The just-stopped process may still hold the file for a moment.
                if time.monotonic() >= deadline:
                    raise UpdateError(f"{source} is still locked: {error}") from error
                time.sleep(_RETRY_INTERVAL_SECONDS)
