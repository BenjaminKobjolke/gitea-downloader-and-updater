"""Settings for one updater run, built from CLI args and environment."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from gitea_updater.constants import (
    ENV_EXE,
    EXE_SUFFIX,
    HTTP_TIMEOUT_SECONDS,
    START_CHECK_SECONDS,
    STOP_TIMEOUT_SECONDS,
    UNLOCK_TIMEOUT_SECONDS,
)
from gitea_updater.errors import UpdateError


@dataclass(frozen=True)
class Settings:
    exe_path: Path
    force: bool = False
    http_timeout_seconds: float = HTTP_TIMEOUT_SECONDS
    stop_timeout_seconds: float = STOP_TIMEOUT_SECONDS
    unlock_timeout_seconds: float = UNLOCK_TIMEOUT_SECONDS
    start_check_seconds: float = START_CHECK_SECONDS

    @classmethod
    def create(cls, exe_arg: str | None, force: bool, environ: Mapping[str, str]) -> "Settings":
        """Validate the exe path (CLI arg first, then GITEA_EXE) and build Settings."""
        raw = exe_arg or environ.get(ENV_EXE)
        if not raw:
            raise UpdateError(f"No Gitea exe given. Pass --exe or set {ENV_EXE}.")
        exe = Path(raw).resolve()
        if exe.suffix.lower() != EXE_SUFFIX:
            raise UpdateError(f"Not an .exe file: {exe}")
        if not exe.is_file():
            raise UpdateError(f"Gitea exe not found: {exe}")
        return cls(exe_path=exe, force=force)
