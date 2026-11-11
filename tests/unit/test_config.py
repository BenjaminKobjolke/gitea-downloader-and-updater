"""Tests for building Settings from CLI args and environment."""

from pathlib import Path

import pytest

from gitea_updater.config import Settings
from gitea_updater.errors import UpdateError


def _exe(tmp_path: Path) -> Path:
    exe = tmp_path / "gitea.exe"
    exe.write_bytes(b"x")
    return exe


def test_cli_path_wins_over_env(tmp_path: Path) -> None:
    exe = _exe(tmp_path)
    settings = Settings.create(str(exe), force=True, environ={"GITEA_EXE": "C:/other.exe"})
    assert settings.exe_path == exe.resolve()
    assert settings.force is True


def test_env_path_used_when_no_cli(tmp_path: Path) -> None:
    exe = _exe(tmp_path)
    settings = Settings.create(None, force=False, environ={"GITEA_EXE": str(exe)})
    assert settings.exe_path == exe.resolve()


def test_missing_path_fails() -> None:
    with pytest.raises(UpdateError):
        Settings.create(None, force=False, environ={})


def test_non_exe_fails(tmp_path: Path) -> None:
    file = tmp_path / "gitea.txt"
    file.write_bytes(b"x")
    with pytest.raises(UpdateError):
        Settings.create(str(file), force=False, environ={})


def test_nonexistent_fails(tmp_path: Path) -> None:
    with pytest.raises(UpdateError):
        Settings.create(str(tmp_path / "gitea.exe"), force=False, environ={})
