"""打包前准备：将汇总依赖 app.py 复制到 vendor/。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
DEST = VENDOR / "app.py"


def find_source() -> Path | None:
    for path in (ROOT.parent / "app.py", ROOT / "app.py"):
        if path.is_file():
            return path
    return None


def main() -> int:
    if DEST.is_file() and find_source() is None:
        print(f"vendor 已存在: {DEST}")
        return 0

    src = find_source()
    if src is None:
        print(
            "未找到 app.py。请将汇总逻辑文件放到 vendor/app.py，"
            "或放在上级目录 app.py 后重试。",
            file=sys.stderr,
        )
        return 1

    VENDOR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, DEST)
    print(f"已复制: {src} -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
