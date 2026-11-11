"""Tests for the CLI entry point's exit codes."""

from pathlib import Path
from unittest.mock import patch

from gitea_updater import cli
from gitea_updater.updater import UpdateResult


def test_missing_exe_exits_1() -> None:
    assert cli.main([], environ={}) == 1


def test_success_exits_0(tmp_path: Path) -> None:
    exe = tmp_path / "gitea.exe"
    exe.write_bytes(b"x")
    with patch("gitea_updater.cli.Updater") as updater_cls:
        updater_cls.return_value.run.return_value = UpdateResult.UP_TO_DATE
        assert cli.main(["--exe", str(exe)], environ={}) == 0
