"""冻结运行时：让 Playwright 能找到驱动与浏览器。"""
import os
import sys
from pathlib import Path


def _apply() -> None:
    if not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).parent
    meipass = Path(getattr(sys, "_MEIPASS", base))
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(base / "ms-playwright")
    driver = meipass / "playwright" / "driver"
    if driver.is_dir():
        os.environ.setdefault("PLAYWRIGHT_DRIVER_PATH", str(driver))


_apply()
