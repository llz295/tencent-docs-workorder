"""将 Playwright Chromium（不含 headless_shell）复制到 dist，并校验 revision 与 chrome.exe。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.playwright_bootstrap import (  # noqa: E402
    chromium_executable,
    chromium_installed,
    expected_chromium_revision,
)


def playwright_cache_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME", "")
    return Path(local) / "ms-playwright"


def project_browsers_dir() -> Path:
    return _ROOT / "ms-playwright"


def is_full_chromium_dir(name: str) -> bool:
    return name.startswith("chromium-") and "headless_shell" not in name


def chromium_ready(browsers_dir: Path) -> bool:
    revision = expected_chromium_revision()
    exe = chromium_executable(browsers_dir)
    if not exe:
        return False
    if revision and f"chromium-{revision}" not in str(exe):
        return False
    # 当 revision 为 None 时（如中文路径导致 browsers.json 不可达），
    # 只要有 chrome.exe 即视为就绪
    if not revision and chromium_installed(browsers_dir):
        return True
    return True


def pick_source_browsers() -> Path | None:
    for src in (project_browsers_dir(), playwright_cache_dir()):
        if chromium_ready(src):
            return src
    return None


def install_chromium_to(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    lock = target / "__dirlock"
    if lock.exists():
        shutil.rmtree(lock, ignore_errors=True)
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(target)
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--no-shell"],
        env=env,
        check=True,
    )
    if not chromium_installed(target):
        raise RuntimeError(f"Chromium 安装失败: {target}")


def ensure_project_chromium() -> Path:
    dst = project_browsers_dir()
    if not chromium_ready(dst):
        # 优先从 Playwright 默认缓存复制，避免重复下载
        cache = playwright_cache_dir()
        if chromium_ready(cache):
            print(f"从 Playwright 缓存复制 Chromium: {cache}")
            copy_chromium_only(cache, dst)
        else:
            revision = expected_chromium_revision()
            if dst.is_dir() and revision:
                stale = dst / f"chromium-{revision}"
                for child in dst.iterdir():
                    if child.is_dir() and child.name.startswith("chromium-") and child != stale:
                        shutil.rmtree(child, ignore_errors=True)
            print(f"安装 Chromium 到 {dst} ...")
            install_chromium_to(dst)
    exe = chromium_executable(dst)
    if not exe:
        raise RuntimeError(f"未找到 chrome.exe: {dst}")
    print(f"Chromium OK: {exe}")
    return dst


def import_from_dist(dist: Path) -> Path:
    """从 dist/WorkOrderAutomation 保留 ms-playwright 到项目目录。"""
    src = dist / "ms-playwright"
    if not chromium_ready(src):
        raise RuntimeError(f"dist 中无可用 Chromium: {src}")
    dst = project_browsers_dir()
    copy_chromium_only(src, dst)
    print(f"已从 dist 保留 Chromium -> {dst}")
    return dst


def copy_chromium_only(src_root: Path, dst_root: Path) -> list[str]:
    if not src_root.is_dir():
        raise FileNotFoundError(f"Playwright 缓存不存在: {src_root}")
    if not chromium_installed(src_root):
        raise RuntimeError(
            f"源目录缺少可用 Chromium，请先执行: python -m playwright install chromium --no-shell\n"
            f"路径: {src_root}"
        )

    revision = expected_chromium_revision()
    copied: list[str] = []
    if dst_root.exists():
        shutil.rmtree(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    links = src_root / ".links"
    if links.is_dir():
        shutil.copytree(links, dst_root / ".links")

    for item in sorted(src_root.iterdir()):
        if not item.is_dir() or not is_full_chromium_dir(item.name):
            continue
        if revision and item.name != f"chromium-{revision}":
            continue
        shutil.copytree(item, dst_root / item.name)
        copied.append(item.name)

    for item in sorted(src_root.iterdir()):
        if not item.is_dir():
            continue
        if item.name in {".links"} or item.name in copied:
            continue
        if item.name.startswith(("ffmpeg-", "winldd-")):
            shutil.copytree(item, dst_root / item.name)

    if not copied:
        raise RuntimeError(
            f"未找到 revision={revision or '?'} 的 Chromium 目录: {src_root}"
        )

    exe = chromium_executable(dst_root)
    if not exe:
        raise RuntimeError(f"复制后缺少 chrome.exe: {dst_root}")
    return copied


def stage_to_dist(dist: Path) -> list[str]:
    src = pick_source_browsers()
    if src is None:
        src = ensure_project_chromium()
    dst = dist / "ms-playwright"
    names = copy_chromium_only(src, dst)
    total = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    print(f"已复制: {', '.join(names)}  ->  {dst}")
    print(f"浏览器体积: {total / (1024 * 1024):.1f} MB")
    return names


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--ensure-project":
        ensure_project_chromium()
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--import-from":
        import_from_dist(Path(sys.argv[2]).resolve())
        return 0
    if len(sys.argv) != 2:
        print(
            "用法:\n"
            "  python build/stage_browsers.py --ensure-project\n"
            "  python build/stage_browsers.py --import-from <dist目录>\n"
            "  python build/stage_browsers.py <dist目录>",
            file=sys.stderr,
        )
        return 2

    dist = Path(sys.argv[1]).resolve()
    stage_to_dist(dist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
