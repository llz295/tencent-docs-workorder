"""
腾讯文档 · 录音师工单自动化 — 唯一入口

默认启动网页版（可局域网访问）；带命令行参数时走 CLI。

用法:
    python run.py                    # 启动网页版（默认）
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
    p.add_argument("--web", action="store_true", help="启动网页版（等同于无参数运行）")
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


def _launch_web(mode: str = "web") -> int:
    """启动网页版（包含 InstanceLock 保护）。"""
    from config.app_config import AppConfig
    from config.instance_lock import InstanceLock

    cfg = AppConfig.load()
    lock = InstanceLock(mode)
    try:
        lock.acquire()
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        print("请先关闭已运行的实例后再启动。", file=sys.stderr)
        return 1

    try:
        from web.server import run_web_server

        run_web_server(host=cfg.web_host, port=cfg.web_port)
        return 0
    finally:
        # 确保锁被释放
        try:
            lock.release()
        except Exception:
            pass


def main() -> int:
    ensure_data_files()
    ensure_chromium_browser()
    argv = sys.argv[1:]

    if not argv:
        # 无参数时默认启动网页版
        return _launch_web()

    if argv == ["--web"] or (len(argv) == 1 and argv[0] in ("web", "--web")):
        return _launch_web()

    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "web", False):
        return _launch_web()

    if args.command is None:
        return _launch_web()

    return _run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
