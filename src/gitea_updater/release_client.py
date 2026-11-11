"""Look up the latest Gitea release on GitHub and download its Windows amd64 exe."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from gitea_updater.constants import (
    DOWNLOAD_CHUNK_BYTES,
    EXE_ASSET_PATTERN,
    RELEASE_API_URL,
    SHA256_SUFFIX,
    TRUSTED_DOWNLOAD_PREFIX,
    USER_AGENT,
)
from gitea_updater.errors import UpdateError
from gitea_updater.version import Version, parse_version


@dataclass(frozen=True)
class GiteaRelease:
    version: Version
    asset_name: str
    exe_url: str
    sha256_url: str


def _trusted_url(asset: Mapping[str, Any]) -> str:
    url = str(asset.get("browser_download_url", ""))
    if not url.startswith(TRUSTED_DOWNLOAD_PREFIX):
        raise UpdateError(f"Refusing download from unexpected URL: {url}")
    return url


def select_release(data: Mapping[str, Any]) -> GiteaRelease:
    """Pick the Windows amd64 exe and its .sha256 from a GitHub release JSON."""
    assets = {str(a.get("name", "")): a for a in data.get("assets", [])}
    exe_names = [name for name in assets if EXE_ASSET_PATTERN.match(name)]
    if len(exe_names) != 1:
        raise UpdateError(f"Expected one Windows amd64 exe in the release, found {exe_names}")
    exe_name = exe_names[0]
    sha_asset = assets.get(exe_name + SHA256_SUFFIX)
    if sha_asset is None:
        raise UpdateError(f"Release has no checksum file {exe_name}{SHA256_SUFFIX}")
    return GiteaRelease(
        version=parse_version(str(data.get("tag_name", ""))),
        asset_name=exe_name,
        exe_url=_trusted_url(assets[exe_name]),
        sha256_url=_trusted_url(sha_asset),
    )


def verify_sha256(file: Path, checksum_text: str) -> None:
    """`checksum_text` is the .sha256 file content: "<hex digest>  <file name>"."""
    expected = checksum_text.strip().split()[0].lower() if checksum_text.strip() else ""
    digest = hashlib.sha256()
    with file.open("rb") as handle:
        for chunk in iter(lambda: handle.read(DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise UpdateError(f"SHA-256 mismatch for {file.name}")


class ReleaseClient:
    """GitHub access for Gitea releases."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    def fetch_latest(self) -> GiteaRelease:
        try:
            data = json.loads(self._read(RELEASE_API_URL))
        except ValueError as error:
            raise UpdateError(f"Invalid JSON from {RELEASE_API_URL}") from error
        return select_release(data)

    def download(self, release: GiteaRelease, target: Path) -> None:
        """Download the exe to `target` and verify it; never leaves a partial file behind."""
        try:
            checksum = self._read(release.sha256_url).decode("ascii", errors="replace")
            with self._open(release.exe_url) as response, target.open("wb") as out:
                for chunk in iter(lambda: response.read(DOWNLOAD_CHUNK_BYTES), b""):
                    out.write(chunk)
            verify_sha256(target, checksum)
        except BaseException:
            target.unlink(missing_ok=True)
            raise

    def _read(self, url: str) -> bytes:
        with self._open(url) as response:
            data: bytes = response.read()
            return data

    def _open(self, url: str) -> Any:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            return urlopen(request, timeout=self._timeout)
        except (URLError, OSError) as error:
            raise UpdateError(f"Download failed for {url}: {error}") from error
