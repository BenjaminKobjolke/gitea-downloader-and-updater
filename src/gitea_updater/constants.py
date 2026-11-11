"""String constants and fixed values shared across the updater."""

import re

RELEASE_API_URL = "https://api.github.com/repos/go-gitea/gitea/releases/latest"
TRUSTED_DOWNLOAD_PREFIX = "https://github.com/go-gitea/gitea/releases/download/"
USER_AGENT = "gitea-updater"

# Gitea up to 1.x named it "-windows-4.0-amd64.exe", newer releases "-windows-amd64.exe".
EXE_ASSET_PATTERN = re.compile(r"^gitea-[\d.]+-windows(?:-4\.0)?-amd64\.exe$")
VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)+)")
SHA256_SUFFIX = ".sha256"
DOWNLOAD_SUFFIX = ".download"
EXE_SUFFIX = ".exe"
BACKUP_DIR_NAME = "backup_gitea"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"

ENV_EXE = "GITEA_EXE"
ENV_LOG_LEVEL = "GITEA_UPDATER_LOG_LEVEL"
DEFAULT_LOG_LEVEL = "INFO"

HTTP_TIMEOUT_SECONDS = 60.0
VERSION_TIMEOUT_SECONDS = 30.0
STOP_TIMEOUT_SECONDS = 30.0
UNLOCK_TIMEOUT_SECONDS = 30.0
START_CHECK_SECONDS = 5.0
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
