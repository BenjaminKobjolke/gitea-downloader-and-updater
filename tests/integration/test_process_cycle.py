"""Integration test: find, stop, swap and restart a real long-running process.

A copy of Windows' ping.exe stands in for gitea: it is a standalone exe that stays alive
for a known time, so we can match it by executable path like the real tool does.
"""

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import psutil
import pytest

from gitea_updater.exe_swapper import ExeSwapper
from gitea_updater.process_control import ProcessController

PING = Path(r"C:\Windows\System32\PING.EXE")


@pytest.fixture
def fake_gitea(tmp_path: Path) -> Iterator[Path]:
    exe = tmp_path / "gitea-1.11.6-windows-4.0-amd64.exe"
    shutil.copy2(PING, exe)
    started = subprocess.Popen(
        [str(exe), "-n", "120", "127.0.0.1"], stdout=subprocess.DEVNULL, cwd=tmp_path
    )
    yield exe
    started.kill()
    for proc in psutil.process_iter(["exe"]):
        if proc.info["exe"] and Path(proc.info["exe"]) == exe:
            proc.kill()


@pytest.mark.skipif(not PING.exists(), reason="needs Windows ping.exe")
def test_stop_swap_start_cycle(fake_gitea: Path, tmp_path: Path) -> None:
    controller = ProcessController(stop_timeout_seconds=10, start_check_seconds=1)
    found = controller.find(fake_gitea)
    assert found is not None
    assert found.cmdline[1:] == ("-n", "120", "127.0.0.1")

    controller.stop(found)
    assert not psutil.pid_exists(found.pid) or psutil.Process(found.pid).status() == "zombie"

    new_file = tmp_path / "gitea-28.3.0-windows-amd64.exe.download"
    shutil.copy2(PING, new_file)
    backup = ExeSwapper(unlock_timeout_seconds=10).swap(fake_gitea, new_file)
    assert backup.exists()

    new_pid = controller.start(found)
    restarted = psutil.Process(new_pid)
    assert restarted.is_running()
    assert Path(restarted.exe()) == fake_gitea
    assert tuple(restarted.cmdline()[1:]) == found.cmdline[1:]
    assert restarted.cwd().rstrip("\\") == str(tmp_path)
