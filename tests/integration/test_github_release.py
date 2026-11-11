"""Integration test against the real GitHub releases API (needs network)."""

from gitea_updater.release_client import ReleaseClient


def test_latest_release_has_windows_amd64_exe_and_checksum() -> None:
    release = ReleaseClient(timeout_seconds=30).fetch_latest()
    assert release.asset_name.endswith("amd64.exe")
    assert release.sha256_url == release.exe_url + ".sha256"
    assert release.version >= (1, 0, 0)
