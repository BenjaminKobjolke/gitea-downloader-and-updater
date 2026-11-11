"""Parse Gitea version strings and read the version of an installed exe."""

import subprocess
from pathlib import Path

from gitea_updater.constants import VERSION_PATTERN, VERSION_TIMEOUT_SECONDS
from gitea_updater.errors import UpdateError

Version = tuple[int, ...]


def parse_version(text: str) -> Version:
    """Return the first dotted number in `text` ("v28.3.0", "Gitea version 1.11.6 ...")."""
    match = VERSION_PATTERN.search(text)
    if match is None:
        raise UpdateError(f"No version number found in: {text!r}")
    return tuple(int(part) for part in match.group(1).split("."))


def format_version(version: Version) -> str:
    return ".".join(str(part) for part in version)


def read_installed_version(exe: Path) -> Version:
    """Ask the exe itself; the file name stays the old one after an update."""
    try:
        result = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise UpdateError(f"Could not run {exe} --version: {error}") from error
    return parse_version(result.stdout)
