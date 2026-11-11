@echo off
REM Update Gitea. Pass --exe <path to gitea exe> or set GITEA_EXE. Extra args are forwarded.
uv run gitea-updater %*
exit /b %ERRORLEVEL%
