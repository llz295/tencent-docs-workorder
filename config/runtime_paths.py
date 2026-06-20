"""运行目录（开发 / PyInstaller / Nuitka 冻结）。"""
import shutil
import sys
from pathlib import Path

from config.frozen_bootstrap import is_frozen


def get_base_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_bundle_dir() -> Path | None:
    if not is_frozen():
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(sys.executable).parent


def ensure_data_files() -> Path:
    """冻结运行时把内置 data 模板复制到 exe 旁（仅缺失时）。"""
    data_dir = get_base_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    bundle = get_bundle_dir()
    if bundle is None:
        return data_dir

    bundled_data = bundle / "data"
    if not bundled_data.is_dir():
        return data_dir

    for src in bundled_data.iterdir():
        dst = data_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
    return data_dir
