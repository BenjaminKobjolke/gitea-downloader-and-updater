"""Orchestrate one update: check, download, stop, swap, start, roll back on failure."""

from collections.abc import Callable
from enum import Enum
from pathlib import Path

from gitea_updater.app_logger import AppLogger
from gitea_updater.config import Settings
from gitea_updater.constants import DOWNLOAD_SUFFIX
from gitea_updater.errors import UpdateError
from gitea_updater.exe_swapper import ExeSwapper
from gitea_updater.process_control import GiteaProcess, ProcessController
from gitea_updater.release_client import ReleaseClient
from gitea_updater.version import Version, format_version


class UpdateResult(Enum):
    UP_TO_DATE = "up to date"
    UPDATED = "updated and restarted"
    UPDATED_NOT_RUNNING = "updated; Gitea was not running, not started"


class Updater:
    def __init__(
        self,
        settings: Settings,
        release_client: ReleaseClient,
        processes: ProcessController,
        swapper: ExeSwapper,
        version_reader: Callable[[Path], Version],
        logger: AppLogger,
    ) -> None:
        self._settings = settings
        self._client = release_client
        self._processes = processes
        self._swapper = swapper
        self._version_reader = version_reader
        self._log = logger

    def run(self) -> UpdateResult:
        exe = self._settings.exe_path
        installed = self._version_reader(exe)
        release = self._client.fetch_latest()
        self._log.info(
            f"Installed {format_version(installed)}, latest {format_version(release.version)}"
        )
        if release.version <= installed and not self._settings.force:
            return UpdateResult.UP_TO_DATE

        download = exe.with_name(release.asset_name + DOWNLOAD_SUFFIX)
        self._log.info(f"Downloading {release.asset_name}")
        self._client.download(release, download)

        running = self._processes.find(exe)
        backup = self._stop_and_swap(exe, download, running)
        self._log.info(f"Old exe moved to {backup}")
        if running is None:
            return UpdateResult.UPDATED_NOT_RUNNING
        self._start_or_roll_back(exe, backup, running)
        return UpdateResult.UPDATED

    def _stop_and_swap(self, exe: Path, download: Path, running: GiteaProcess | None) -> Path:
        if running is not None:
            self._log.info(f"Stopping Gitea (pid {running.pid})")
            try:
                self._processes.stop(running)
            except UpdateError:
                download.unlink(missing_ok=True)
                raise
        try:
            return self._swapper.swap(exe, download)
        except UpdateError:
            # swap() already put the old exe back; bring the old Gitea up again.
            download.unlink(missing_ok=True)
            if running is not None:
                self._processes.start(running)
            raise

    def _start_or_roll_back(self, exe: Path, backup: Path, running: GiteaProcess) -> None:
        try:
            pid = self._processes.start(running)
            self._log.info(f"Gitea started (pid {pid})")
        except UpdateError as start_error:
            self._log.error(f"New Gitea did not start: {start_error}; rolling back")
            try:
                self._swapper.rollback(exe, backup)
                self._processes.start(running)
            except UpdateError as rollback_error:
                raise UpdateError(
                    f"New Gitea did not start ({start_error}) and rollback failed "
                    f"({rollback_error}). Old exe: {backup}"
                ) from rollback_error
            raise UpdateError(
                f"New Gitea did not start ({start_error}); rolled back to the old exe"
            ) from start_error
