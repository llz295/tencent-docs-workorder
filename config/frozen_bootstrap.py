"""PyInstaller / Nuitka 冻结运行时环境初始化。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        return True
    main = sys.modules.get("__main__")
    return main is not None and getattr(main, "__compiled__", False)


def apply_frozen_env() -> None:
    if not is_frozen():
        return
    base = Path(sys.executable).parent
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(base / "ms-playwright")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        driver = Path(meipass) / "playwright" / "driver"
        if driver.is_dir():
            os.environ.setdefault("PLAYWRIGHT_DRIVER_PATH", str(driver))
        return

    for candidate in (
        base / "playwright" / "driver",
        base / "playwright.driver",
    ):
        if candidate.is_dir():
            os.environ.setdefault("PLAYWRIGHT_DRIVER_PATH", str(candidate))
            break
