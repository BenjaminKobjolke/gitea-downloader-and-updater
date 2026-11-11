"""Tests for the update orchestration with spec'd collaborators."""

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from gitea_updater.app_logger import AppLogger
from gitea_updater.config import Settings
from gitea_updater.errors import UpdateError
from gitea_updater.exe_swapper import ExeSwapper
from gitea_updater.process_control import GiteaProcess, ProcessController
from gitea_updater.release_client import GiteaRelease, ReleaseClient
from gitea_updater.updater import Updater, UpdateResult

EXE = Path("E:/git/gitea-1.11.6-windows-4.0-amd64.exe")
BACKUP = Path("E:/git/backup_gitea/gitea-1.11.6-windows-4.0-amd64.exe")
DOWNLOAD = Path("E:/git/gitea-28.3.0-windows-amd64.exe.download")
RELEASE = GiteaRelease(
    version=(28, 3, 0),
    asset_name="gitea-28.3.0-windows-amd64.exe",
    exe_url="https://github.com/x.exe",
    sha256_url="https://github.com/x.exe.sha256",
)
RUNNING = GiteaProcess(pid=42, exe=EXE, cmdline=(str(EXE), "web"), cwd="E:/git", environ=None)


class Fixture:
    def __init__(self, installed: tuple[int, ...], force: bool = False) -> None:
        self.client = MagicMock(spec=ReleaseClient)
        self.client.fetch_latest.return_value = RELEASE
        self.processes = MagicMock(spec=ProcessController)
        self.processes.find.return_value = RUNNING
        self.processes.start.return_value = 43
        self.swapper = MagicMock(spec=ExeSwapper)
        self.swapper.swap.return_value = BACKUP
        self.parent = MagicMock()
        self.parent.attach_mock(self.processes, "processes")
        self.parent.attach_mock(self.swapper, "swapper")
        self.updater = Updater(
            settings=Settings(exe_path=EXE, force=force),
            release_client=self.client,
            processes=self.processes,
            swapper=self.swapper,
            version_reader=lambda _exe: installed,
            logger=MagicMock(spec=AppLogger),
        )


def test_up_to_date_does_nothing() -> None:
    fx = Fixture(installed=(28, 3, 0))
    assert fx.updater.run() == UpdateResult.UP_TO_DATE
    fx.client.download.assert_not_called()
    fx.processes.stop.assert_not_called()


def test_force_updates_same_version() -> None:
    fx = Fixture(installed=(28, 3, 0), force=True)
    assert fx.updater.run() == UpdateResult.UPDATED
    fx.client.download.assert_called_once_with(RELEASE, DOWNLOAD)


def test_update_stops_swaps_starts_in_order() -> None:
    fx = Fixture(installed=(1, 11, 6))
    assert fx.updater.run() == UpdateResult.UPDATED
    assert fx.parent.mock_calls == [
        call.processes.find(EXE),
        call.processes.stop(RUNNING),
        call.swapper.swap(EXE, DOWNLOAD),
        call.processes.start(RUNNING),
    ]


def test_not_running_swaps_without_start() -> None:
    fx = Fixture(installed=(1, 11, 6))
    fx.processes.find.return_value = None
    assert fx.updater.run() == UpdateResult.UPDATED_NOT_RUNNING
    fx.swapper.swap.assert_called_once_with(EXE, DOWNLOAD)
    fx.processes.start.assert_not_called()


def test_start_failure_rolls_back_and_restarts_old() -> None:
    fx = Fixture(installed=(1, 11, 6))
    fx.processes.start.side_effect = [UpdateError("died"), 43]
    with pytest.raises(UpdateError, match="rolled back"):
        fx.updater.run()
    assert fx.parent.mock_calls[-3:] == [
        call.processes.start(RUNNING),
        call.swapper.rollback(EXE, BACKUP),
        call.processes.start(RUNNING),
    ]


def test_swap_failure_restarts_old_gitea() -> None:
    fx = Fixture(installed=(1, 11, 6))
    fx.swapper.swap.side_effect = UpdateError("locked")
    with pytest.raises(UpdateError, match="locked"):
        fx.updater.run()
    fx.processes.start.assert_called_once_with(RUNNING)


def test_rollback_failure_reports_both() -> None:
    fx = Fixture(installed=(1, 11, 6))
    fx.processes.start.side_effect = UpdateError("died")
    fx.swapper.rollback.side_effect = UpdateError("rollback broke")
    with pytest.raises(UpdateError, match="rollback broke"):
        fx.updater.run()
