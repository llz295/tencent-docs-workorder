"""单实例锁：桌面版与网页版不可同时运行。"""
from __future__ import annotations

import atexit
import os
import sys
from pathlib import Path

from config.runtime_paths import ensure_data_files


def _lock_path() -> Path:
    return ensure_data_files() / "instance.lock"


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class InstanceLock:
    def __init__(self, mode: str):
        self.mode = mode
        self._path = _lock_path()
        self._held = False

    def acquire(self) -> None:
        if self._path.is_file():
            try:
                lines = self._path.read_text(encoding="utf-8").strip().splitlines()
                pid = int(lines[0])
                old_mode = lines[1] if len(lines) > 1 else "unknown"
            except (ValueError, OSError):
                pid, old_mode = 0, "unknown"
            if _is_pid_alive(pid):
                label = "桌面程序" if old_mode == "desktop" else "网页版"
                raise RuntimeError(
                    f"程序已在运行（{label}，进程 {pid}）。请先关闭后再启动。"
                )
            self._path.unlink(missing_ok=True)

        self._path.write_text(f"{os.getpid()}\n{self.mode}\n", encoding="utf-8")
        self._held = True
        atexit.register(self.release)

    def release(self) -> None:
        if not self._held:
            return
        try:
            if self._path.is_file():
                lines = self._path.read_text(encoding="utf-8").strip().splitlines()
                if lines and int(lines[0]) == os.getpid():
                    self._path.unlink()
        except (ValueError, OSError):
            pass
        self._held = False
