"""Tests for version parsing and reading the installed Gitea version."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from gitea_updater.errors import UpdateError
from gitea_updater.version import parse_version, read_installed_version


def test_parse_version_from_gitea_output() -> None:
    text = "Gitea version 1.11.6 built with GNU Make 4.1, go1.13.15 : bindata, sqlite"
    assert parse_version(text) == (1, 11, 6)


def test_parse_version_from_tag() -> None:
    assert parse_version("v28.3.0") == (28, 3, 0)


def test_parse_version_rejects_garbage() -> None:
    with pytest.raises(UpdateError):
        parse_version("no version here")


def test_versions_compare_numerically() -> None:
    assert parse_version("v28.3.0") > parse_version("Gitea version 1.27.3")


def test_read_installed_version_runs_exe(tmp_path: Path) -> None:
    exe = tmp_path / "gitea.exe"
    done = subprocess.CompletedProcess([str(exe)], 0, stdout="Gitea version 1.21.4 built\n")
    with patch("gitea_updater.version.subprocess.run", return_value=done) as run:
        assert read_installed_version(exe) == (1, 21, 4)
    assert run.call_args.args[0] == [str(exe), "--version"]


def test_read_installed_version_reports_failure(tmp_path: Path) -> None:
    with (
        patch("gitea_updater.version.subprocess.run", side_effect=OSError("boom")),
        pytest.raises(UpdateError),
    ):
        read_installed_version(tmp_path / "gitea.exe")
