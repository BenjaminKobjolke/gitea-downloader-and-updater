"""Command-line entry point and the central error handler."""

import argparse
import os
from collections.abc import Mapping, Sequence

from gitea_updater.app_logger import AppLogger
from gitea_updater.config import Settings
from gitea_updater.constants import ENV_EXE
from gitea_updater.errors import UpdateError
from gitea_updater.exe_swapper import ExeSwapper
from gitea_updater.process_control import ProcessController
from gitea_updater.release_client import ReleaseClient
from gitea_updater.updater import Updater
from gitea_updater.version import read_installed_version


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gitea-updater",
        description="Replace a running Gitea exe with the latest Windows amd64 release.",
    )
    parser.add_argument("--exe", help=f"Gitea exe to update (default: ${ENV_EXE})")
    parser.add_argument(
        "--force", action="store_true", help="update even if already on the latest version"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    logger = AppLogger()
    args = _parse_args(argv)
    try:
        settings = Settings.create(args.exe, args.force, os.environ if environ is None else environ)
        updater = Updater(
            settings=settings,
            release_client=ReleaseClient(settings.http_timeout_seconds),
            processes=ProcessController(
                settings.stop_timeout_seconds, settings.start_check_seconds
            ),
            swapper=ExeSwapper(settings.unlock_timeout_seconds),
            version_reader=read_installed_version,
            logger=logger,
        )
        result = updater.run()
    except UpdateError as error:
        logger.error(str(error))
        return 1
    except Exception as error:  # noqa: BLE001 - last-resort handler, logs the trace
        logger.error(f"Unexpected error: {error}", with_trace=True)
        return 1
    logger.info(f"Done: {result.value}")
    return 0
