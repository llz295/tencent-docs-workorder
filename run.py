"""
腾讯文档 · 录音师工单自动化 — 唯一入口

默认启动图形界面；带命令行参数时走 CLI（兼容原 main.py / summarize_main.py）。

用法:
    python run.py                    # 选择桌面/网页版后启动
    python run.py --web              # 强制网页版
    python run.py --gui              # 强制桌面 GUI
    python run.py download           # 仅下载（CLI）
    python run.py summarize          # 仅汇总
    python run.py all                # 下载并汇总
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.frozen_bootstrap import apply_frozen_env
from config.playwright_bootstrap import ensure_chromium_browser
from config.runtime_paths import ensure_data_files

apply_frozen_env()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="腾讯文档录音师工单自动化")
    sub = p.add_subparsers(dest="command")

    dl = sub.add_parser("download", help="批量下载工单")
    dl.add_argument("-w", "--workers", type=int, default=None)

    sm = sub.add_parser("summarize", help="汇总工单")
    sm.add_argument("-y", "--yes", action="store_true", help="跳过汇总确认")
    sm.add_argument("--sheet", default=None)
    sm.add_argument("--no-sheet-prompt", action="store_true")
    sm.add_argument("--no-date-prompt", action="store_true")

    both = sub.add_parser("all", help="下载后汇总")
    both.add_argument("-w", "--workers", type=int, default=None)
    both.add_argument("-y", "--yes", action="store_true")

    p.add_argument("--gui", action="store_true", help="强制打开桌面 GUI")
    p.add_argument("--web", action="store_true", help="强制打开网页版")
    return p


def _run_cli(args: argparse.Namespace) -> int:
    from core.pipeline import (
        run_download_sync,
        run_download_then_summarize_sync,
        run_summarize,
    )

    cmd = args.command
    if cmd == "download":
        run_download_sync(workers=args.workers)
        return 0
    if cmd == "summarize":
        try:
            run_summarize(
                skip_prompt=args.yes,
                skip_sheet_prompt=args.no_sheet_prompt,
                skip_date_prompt=args.no_date_prompt,
                sheet_name=args.sheet,
            )
        except RuntimeError:
            return 1
        return 0
    if cmd == "all":
        run_download_then_summarize_sync(
            workers=args.workers,
            skip_summarize_prompt=args.yes,
        )
        return 0
    return 1


def _show_lock_error(message: str) -> None:
    print(message, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror("无法启动", message)
        root.destroy()
    except Exception:
        pass


def _launch_ui(*, force_desktop: bool = False, force_web: bool = False) -> int:
    from config.app_config import AppConfig
    from config.instance_lock import InstanceLock
    from config.launch_selector import resolve_launch_mode

    cfg = AppConfig.load()
    if force_web:
        mode = "web"
    elif force_desktop:
        mode = "desktop"
    else:
        mode = resolve_launch_mode(cfg)
        cfg = AppConfig.load()

    lock = InstanceLock(mode)
    try:
        lock.acquire()
    except RuntimeError as exc:
        _show_lock_error(str(exc))
        return 1

    if mode == "web":
        from web.server import run_web_server

        run_web_server(host=cfg.web_host, port=cfg.web_port)
        return 0

    from ui.main_window import launch

    launch()
    return 0


def main() -> int:
    ensure_data_files()
    ensure_chromium_browser()
    argv = sys.argv[1:]

    if not argv:
        return _launch_ui()

    if argv == ["--gui"] or (len(argv) == 1 and argv[0] in ("gui", "--gui")):
        return _launch_ui(force_desktop=True)

    if argv == ["--web"] or (len(argv) == 1 and argv[0] in ("web", "--web")):
        return _launch_ui(force_web=True)

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.web:
        return _launch_ui(force_web=True)
    if args.gui or args.command is None:
        return _launch_ui(force_desktop=True)
    return _run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
