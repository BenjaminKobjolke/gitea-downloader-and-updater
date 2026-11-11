"""Central logger: the only place that talks to `logging` or writes to the console."""

import logging
import os
import sys

from gitea_updater.constants import DEFAULT_LOG_LEVEL, ENV_LOG_LEVEL


class AppLogger:
    """Thin wrapper around `logging`; level comes from GITEA_UPDATER_LOG_LEVEL."""

    def __init__(self, name: str = "gitea_updater") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(os.getenv(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper())

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str, with_trace: bool = False) -> None:
        self._logger.error(message, exc_info=with_trace)
