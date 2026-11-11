"""Find, stop and restart the Gitea process by its exe path."""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

from gitea_updater.errors import UpdateError


@dataclass(frozen=True)
class GiteaProcess:
    """What is needed to start Gitea again exactly as it ran. May hold secrets: never log."""

    pid: int
    exe: Path
    cmdline: tuple[str, ...]
    cwd: str
    environ: dict[str, str] | None


def _same_path(a: str, b: Path) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(str(b))


class ProcessController:
    def __init__(self, stop_timeout_seconds: float, start_check_seconds: float) -> None:
        self._stop_timeout = stop_timeout_seconds
        self._start_check = start_check_seconds

    def find(self, exe: Path) -> GiteaProcess | None:
        """Return the one process running `exe`, or None. Several matches is an error."""
        matches = []
        for proc in psutil.process_iter(["exe"]):
            path = proc.info.get("exe")
            if path and _same_path(path, exe):
                matches.append(proc)
        if not matches:
            return None
        if len(matches) > 1:
            pids = [p.pid for p in matches]
            raise UpdateError(f"Several processes run {exe} (pids {pids}); stop extras first")
        return self._describe(matches[0], exe)

    def stop(self, process: GiteaProcess) -> None:
        try:
            proc = psutil.Process(process.pid)
            proc.terminate()
            try:
                proc.wait(timeout=self._stop_timeout)
            except psutil.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=self._stop_timeout)
        except psutil.NoSuchProcess:
            return
        except (psutil.AccessDenied, psutil.TimeoutExpired) as error:
            raise UpdateError(f"Could not stop Gitea (pid {process.pid}): {error}") from error

    def start(self, process: GiteaProcess) -> int:
        """Start detached with the captured args; return the pid once it stayed alive."""
        # Use the absolute exe: Popen resolves a relative argv[0] against *our* cwd.
        args = [str(process.exe), *process.cmdline[1:]]
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            child = subprocess.Popen(
                args,
                cwd=process.cwd,
                env=process.environ,
                creationflags=flags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError as error:
            raise UpdateError(f"Could not start {process.exe}: {error}") from error
        time.sleep(self._start_check)
        code = child.poll()
        if code is not None:
            raise UpdateError(f"Gitea exited right after start with code {code}")
        return child.pid

    @staticmethod
    def _describe(proc: psutil.Process, exe: Path) -> GiteaProcess:
        try:
            cmdline = tuple(proc.cmdline())
            cwd = proc.cwd()
        except psutil.Error as error:
            raise UpdateError(
                f"Cannot read Gitea's command line (pid {proc.pid}): {error}"
            ) from error
        try:
            environ: dict[str, str] | None = proc.environ()
        except psutil.Error:
            environ = None  # best effort; the child then inherits our environment
        return GiteaProcess(pid=proc.pid, exe=exe, cmdline=cmdline, cwd=cwd, environ=environ)
