# gitea-updater

Updates a Gitea that runs on Windows as a plain process from a single exe.

One run:

1. reads the installed version (`<exe> --version`),
2. asks GitHub for the latest Gitea release and picks the Windows amd64 exe,
3. downloads it next to the old exe and checks its SHA-256,
4. stops the running Gitea (found by its exe path),
5. moves the old exe to `backup_gitea\` next to it,
6. puts the new exe in place **under the old file name**,
7. starts Gitea again with the same command line, working dir and environment.

If the new Gitea does not start, the old exe is put back and started again.

Example: `E:\git\gitea-1.11.6-windows-4.0-amd64.exe` is running. After the update the
same path holds the latest release and the old file is in
`E:\git\backup_gitea\gitea-1.11.6-windows-4.0-amd64.exe`. If that backup name is taken,
a timestamp is appended.

## Requirements

- Windows, Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Network access to `api.github.com` and `github.com`
- Dependencies: `psutil` (dev: pytest, ruff, mypy)

## Setup

```bat
install.bat
```

## Usage

```bat
start.bat --exe E:\git\gitea-1.11.6-windows-4.0-amd64.exe
```

Or set the path once:

```bat
set GITEA_EXE=E:\git\gitea-1.11.6-windows-4.0-amd64.exe
start.bat
```

Options:

| Option | Meaning |
|---|---|
| `--exe PATH` | Gitea exe to update. Falls back to the `GITEA_EXE` environment variable. |
| `--force` | Download and swap even if the installed version is already the latest. |

Environment: `GITEA_UPDATER_LOG_LEVEL` (`DEBUG`, `INFO` default, `WARNING`, `ERROR`).

Exit code `0` = updated or already up to date, `1` = error.

## Warnings

- **Back up the Gitea data and database first.** Gitea runs database migrations when the
  new version starts. Big jumps (for example 1.11 → current) may need intermediate versions;
  read the Gitea release notes. The tool backs up only the exe.
- If the new version starts, migrates the database, and then exits, the rollback starts the
  old exe on a migrated database. Restore your data backup in that case.
- Run the tool as the same user that started Gitea (elevated if Gitea runs elevated),
  otherwise it cannot stop the process or read its command line.
- If Gitea is not running, the exe is still swapped but Gitea is not started (the tool
  does not guess its arguments).

## Development

```bat
tools\run_tests.bat
tools\run_integration_tests.bat
update.bat
```

Integration tests call the real GitHub API and start/stop a copy of `ping.exe`.

## License

MIT, see [LICENSE](LICENSE).
