"""分发包：确保 exe 旁 ms-playwright 内仅有 Chromium（扫码登录 + 无头下载）。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config.runtime_paths import get_base_dir


def _browsers_dir() -> Path:
    return get_base_dir() / "ms-playwright"


def _browsers_json_path() -> Path | None:
    try:
        import playwright

        path = Path(playwright.__file__).resolve().parent / "driver" / "package" / "browsers.json"
        if path.is_file():
            return path
    except Exception:
        pass
    return None


def expected_chromium_revision() -> str | None:
    path = _browsers_json_path()
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("browsers", []):
            if item.get("name") == "chromium":
                return str(item["revision"])
    except Exception:
        return None
    return None


def chromium_executable(browsers_dir: Path | None = None) -> Path | None:
    root = browsers_dir or _browsers_dir()
    revision = expected_chromium_revision()
    if revision:
        for sub_dir in ("chrome-win64", "chrome-win"):
            exe = root / f"chromium-{revision}" / sub_dir / "chrome.exe"
            if exe.is_file():
                return exe
    if not root.is_dir():
        return None
    for child in sorted(root.iterdir(), reverse=True):
        if child.is_dir() and child.name.startswith("chromium-") and "headless_shell" not in child.name:
            for sub_dir in ("chrome-win64", "chrome-win"):
                exe = child / sub_dir / "chrome.exe"
                if exe.is_file():
                    return exe
    return None


def chromium_installed(browsers_dir: Path | None = None) -> bool:
    return chromium_executable(browsers_dir) is not None


def apply_playwright_env() -> Path:
    """固定浏览器目录为项目内 ms-playwright（仅 Chromium，不含 Firefox/WebKit）。"""
    browsers = _browsers_dir()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
    return browsers


def _remove_non_chromium_browsers(browsers: Path) -> None:
    """仅保留 Chromium 及 Playwright 依赖（ffmpeg/winldd），去掉 headless_shell / firefox / webkit。"""
    if not browsers.is_dir():
        return
    keep_prefixes = ("chromium-", "ffmpeg-", "winldd-")
    revision = expected_chromium_revision()
    for child in browsers.iterdir():
        if not child.is_dir() or child.name == ".links":
            continue
        name = child.name
        if name.startswith("chromium-") and revision and name != f"chromium-{revision}":
            shutil.rmtree(child, ignore_errors=True)
            continue
        if name.startswith(keep_prefixes) and "headless_shell" not in name:
            continue
        shutil.rmtree(child, ignore_errors=True)


def ensure_chromium_browser(*, interactive: bool = True) -> None:
    """缺失或版本不匹配时安装 Chromium 到 exe 同目录 ms-playwright（需联网）。"""
    browsers = apply_playwright_env()
    if chromium_installed(browsers):
        _remove_non_chromium_browsers(browsers)
        return

    revision = expected_chromium_revision() or "?"
    msg = (
        f"首次运行需要下载 Chromium 浏览器（revision {revision}，约 400MB），请保持网络畅通。\n"
        "下载完成后会自动继续。"
    )
    if interactive:
        print(msg)

    browsers.mkdir(parents=True, exist_ok=True)
    from playwright._impl._driver import compute_driver_executable, get_driver_env

    node, cli = compute_driver_executable()
    env = get_driver_env()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
    subprocess.run(
        [node, cli, "install", "chromium", "--no-shell"],
        env=env,
        check=True,
    )
    if not chromium_installed(browsers):
        raise RuntimeError(
            f"Chromium 安装后仍不可用，请检查 {browsers} 下是否存在 chrome.exe"
        )
    _remove_non_chromium_browsers(browsers)
