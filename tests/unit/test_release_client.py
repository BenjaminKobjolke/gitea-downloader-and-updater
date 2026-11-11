"""Tests for picking the Windows amd64 asset and verifying downloads."""

import hashlib
import io
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from gitea_updater.errors import UpdateError
from gitea_updater.release_client import ReleaseClient, select_release, verify_sha256

BASE = "https://github.com/go-gitea/gitea/releases/download/v28.3.0/"
NEW_EXE = "gitea-28.3.0-windows-amd64.exe"


def _asset(name: str) -> dict[str, str]:
    return {"name": name, "browser_download_url": BASE + name}


def _release(*names: str) -> dict[str, Any]:
    return {"tag_name": "v28.3.0", "assets": [_asset(n) for n in names]}


def test_select_release_new_naming() -> None:
    release = select_release(
        _release(
            "gitea-28.3.0-windows-arm64.exe",
            NEW_EXE + ".xz",
            NEW_EXE,
            NEW_EXE + ".sha256",
        )
    )
    assert release.version == (28, 3, 0)
    assert release.asset_name == NEW_EXE
    assert release.exe_url == BASE + NEW_EXE
    assert release.sha256_url == BASE + NEW_EXE + ".sha256"


def test_select_release_old_naming() -> None:
    old = "gitea-1.21.4-windows-4.0-amd64.exe"
    release = select_release(_release(old, old + ".sha256"))
    assert release.asset_name == old


def test_select_release_without_sha256_fails() -> None:
    with pytest.raises(UpdateError):
        select_release(_release(NEW_EXE))


def test_select_release_rejects_foreign_host() -> None:
    data = _release(NEW_EXE, NEW_EXE + ".sha256")
    data["assets"][0]["browser_download_url"] = "https://evil.example/gitea.exe"
    with pytest.raises(UpdateError):
        select_release(data)


def test_verify_sha256_ok(tmp_path: Path) -> None:
    file = tmp_path / "a.exe"
    file.write_bytes(b"gitea")
    verify_sha256(file, hashlib.sha256(b"gitea").hexdigest() + "  a.exe\n")


def test_verify_sha256_mismatch(tmp_path: Path) -> None:
    file = tmp_path / "a.exe"
    file.write_bytes(b"gitea")
    with pytest.raises(UpdateError):
        verify_sha256(file, "0" * 64 + "  a.exe")


def _fake_urlopen(payloads: dict[str, bytes]) -> Any:
    def opener(request: Any, timeout: float) -> io.BytesIO:
        return io.BytesIO(payloads[request.full_url])

    return opener


def test_download_writes_verified_file(tmp_path: Path) -> None:
    release = select_release(_release(NEW_EXE, NEW_EXE + ".sha256"))
    digest = hashlib.sha256(b"new-gitea").hexdigest()
    payloads = {release.exe_url: b"new-gitea", release.sha256_url: digest.encode()}
    target = tmp_path / "x.download"
    with patch("gitea_updater.release_client.urlopen", _fake_urlopen(payloads)):
        ReleaseClient(timeout_seconds=5).download(release, target)
    assert target.read_bytes() == b"new-gitea"


def test_download_deletes_file_on_bad_checksum(tmp_path: Path) -> None:
    release = select_release(_release(NEW_EXE, NEW_EXE + ".sha256"))
    payloads = {release.exe_url: b"tampered", release.sha256_url: b"0" * 64}
    target = tmp_path / "x.download"
    with (
        patch("gitea_updater.release_client.urlopen", _fake_urlopen(payloads)),
        pytest.raises(UpdateError),
    ):
        ReleaseClient(timeout_seconds=5).download(release, target)
    assert not target.exists()
