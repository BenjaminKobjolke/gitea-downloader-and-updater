"""Tests for moving the old exe to backup_gitea and the new one into its place."""

from datetime import datetime
from pathlib import Path

import pytest

from gitea_updater.errors import UpdateError
from gitea_updater.exe_swapper import ExeSwapper, backup_path_for

NOW = datetime(2026, 11, 11, 10, 30, 0)
OLD_NAME = "gitea-1.11.6-windows-4.0-amd64"


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    exe = tmp_path / f"{OLD_NAME}.exe"
    exe.write_bytes(b"old")
    new = tmp_path / "gitea-28.3.0-windows-amd64.exe.download"
    new.write_bytes(b"new")
    return exe, new


def test_backup_path_plain(tmp_path: Path) -> None:
    exe, _ = _setup(tmp_path)
    assert backup_path_for(exe, NOW) == tmp_path / "backup_gitea" / exe.name


def test_backup_path_collision_gets_timestamp_then_counter(tmp_path: Path) -> None:
    exe, _ = _setup(tmp_path)
    backup_dir = tmp_path / "backup_gitea"
    backup_dir.mkdir()
    (backup_dir / exe.name).write_bytes(b"x")
    stamped = backup_dir / f"{OLD_NAME}-20261111-103000.exe"
    assert backup_path_for(exe, NOW) == stamped
    stamped.write_bytes(b"x")
    assert backup_path_for(exe, NOW).name == f"{OLD_NAME}-20261111-103000-2.exe"


def test_swap_keeps_old_name(tmp_path: Path) -> None:
    exe, new = _setup(tmp_path)
    backup = ExeSwapper(unlock_timeout_seconds=1).swap(exe, new)
    assert exe.read_bytes() == b"new"
    assert backup.read_bytes() == b"old"
    assert backup.parent.name == "backup_gitea"
    assert not new.exists()


def test_swap_restores_old_exe_when_new_file_missing(tmp_path: Path) -> None:
    exe, new = _setup(tmp_path)
    new.unlink()
    with pytest.raises(UpdateError):
        ExeSwapper(unlock_timeout_seconds=1).swap(exe, new)
    assert exe.read_bytes() == b"old"


def test_rollback_puts_backup_back(tmp_path: Path) -> None:
    exe, new = _setup(tmp_path)
    swapper = ExeSwapper(unlock_timeout_seconds=1)
    backup = swapper.swap(exe, new)
    swapper.rollback(exe, backup)
    assert exe.read_bytes() == b"old"
    assert not backup.exists()
