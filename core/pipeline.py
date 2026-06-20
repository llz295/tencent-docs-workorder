"""统一下载 / 汇总流程（CLI 与 GUI 共用）。"""
from __future__ import annotations

import asyncio
import contextlib
import io
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

from summarize.date_filter import DateRange

from config.app_config import AppConfig
from config.download_settings import DownloadConfig
from config.settings import DOWNLOAD_DIR, HEADLESS, apply_app_config
from config.summarize_settings import SummarizeConfig
from playwright.async_api import async_playwright

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    print(msg, flush=True)


@contextlib.contextmanager
def capture_stdout(log: LogFn):
    """将 print 重定向到 GUI 日志回调。"""
    buf = io.StringIO()

    class Tee(io.TextIOBase):
        def write(self, s: str) -> int:
            if s:
                log(s.rstrip("\n") if s.endswith("\n") else s)
                buf.write(s)
            return len(s)

        def flush(self) -> None:
            pass

    old = sys.stdout
    sys.stdout = Tee()
    try:
        yield
    finally:
        sys.stdout = old


async def run_download(
    *,
    workers: Optional[int] = None,
    log: LogFn = _default_log,
) -> None:
    apply_app_config()
    download_config = DownloadConfig.load(cli_concurrency=workers)

    with capture_stdout(log):
        log("=" * 50)
        log("腾讯文档批量下载")
        log("=" * 50)

        async with async_playwright() as playwright:
            from auth.session_manager import SessionManager
            from services.download_service import DownloadService

            session_mgr = SessionManager(playwright)
            context, factory = await session_mgr.ensure_session(headless=HEADLESS)
            try:
                service = DownloadService(context, download_config)
                await service.run_all()
            finally:
                await context.close()
                await factory.close()


def run_download_sync(*, workers: Optional[int] = None, log: LogFn = _default_log) -> None:
    asyncio.run(run_download(workers=workers, log=log))


StatusFn = Callable[[str], None]


def _emit_status(status_fn: Optional[StatusFn], msg: str, log: LogFn) -> None:
    log(msg)
    if status_fn:
        status_fn(msg)


def prepare_summarize(
    *,
    skip_prompt: bool = False,
    skip_sheet_prompt: bool = False,
    skip_date_prompt: bool = False,
    sheet_name: Optional[str] = None,
    log: LogFn = _default_log,
    status_fn: Optional[StatusFn] = None,
    tk_parent: Optional["tk.Misc"] = None,
) -> Optional[Tuple[SummarizeConfig, List[DateRange]]]:
    """主线程：确认弹窗、选 sheet、选时间段（含 Tk 交互）。"""
    from summarize.date_range_picker import pick_date_ranges
    from summarize.prompt_dialog import confirm_summarize
    from summarize.sheet_selector import find_sample_xlsx, resolve_sheet_name

    apply_app_config()
    config = SummarizeConfig.load(
        cli_sheet=sheet_name,
        cli_prompt_sheet=False if skip_sheet_prompt else None,
        cli_prompt_date=False if skip_date_prompt else None,
        cli_prompt=False if skip_prompt else None,
    )

    _emit_status(status_fn, "录音师工单汇总 — 准备中", log)

    if not skip_prompt and config.prompt_before_summarize:
        _emit_status(status_fn, "等待确认是否汇总…", log)
        if not confirm_summarize(enabled=True, parent=tk_parent):
            log("[i] 已跳过汇总")
            return None

    if config.prompt_for_sheet_name and not skip_sheet_prompt:
        _emit_status(status_fn, "请选择工作表…", log)
    sample = find_sample_xlsx(
        Path(DOWNLOAD_DIR),
        prefer_name_contains=config.sample_file_keyword,
        output_prefix=config.output_filename_prefix,
    )
    interactive_sheet = config.prompt_for_sheet_name and not skip_sheet_prompt
    resolved = resolve_sheet_name(
        sample,
        config_sheet=config.sheet_name,
        cli_sheet=sheet_name,
        prompt_interactive=interactive_sheet,
        parent=tk_parent,
    )
    if interactive_sheet and resolved is None:
        log("[i] 已取消工作表选择")
        return None
    config = replace(config, sheet_name=resolved)

    ranges: List[DateRange] = []
    if config.prompt_for_date_ranges and not skip_date_prompt:
        _emit_status(status_fn, "请选择时间段（日历）…", log)
        picked = pick_date_ranges(parent=tk_parent)
        if picked is None:
            log("[i] 已取消时间段选择")
            return None
        ranges = picked

    return config, ranges


def run_summarize_core(
    config: SummarizeConfig,
    date_ranges: Optional[List[DateRange]] = None,
    *,
    log: LogFn = _default_log,
    status_fn: Optional[StatusFn] = None,
) -> Optional[Path]:
    """后台线程：读取工单并写入 Excel（无 Tk 弹窗）。"""
    from summarize.aggregator import WorkOrderAggregator

    apply_app_config()
    aggregator = WorkOrderAggregator(config)
    try:
        return aggregator.aggregate(
            skip_prompt=True,
            skip_date_prompt=True,
            date_ranges=date_ranges or [],
            status_fn=status_fn,
            log_fn=log,
        )
    except SystemExit:
        log("[i] 已取消汇总")
        return None
    except RuntimeError as exc:
        log(f"[!] 汇总失败: {exc}")
        raise


def run_summarize(
    *,
    skip_prompt: bool = False,
    skip_sheet_prompt: bool = False,
    skip_date_prompt: bool = False,
    sheet_name: Optional[str] = None,
    log: LogFn = _default_log,
    status_fn: Optional[StatusFn] = None,
    show_notify_dialog: bool = True,
) -> Optional[Path]:
    apply_app_config()
    with capture_stdout(log):
        log("=" * 50)
        log("录音师工单汇总")
        log("=" * 50)

        prep = prepare_summarize(
            skip_prompt=skip_prompt,
            skip_sheet_prompt=skip_sheet_prompt,
            skip_date_prompt=skip_date_prompt,
            sheet_name=sheet_name,
            log=log,
            status_fn=status_fn,
        )
        if prep is None:
            return None
        config, ranges = prep

        output_path = run_summarize_core(
            config, ranges, log=log, status_fn=status_fn
        )

        if output_path is not None and show_notify_dialog:
            from summarize.notify import notify_summarize_saved

            notify_summarize_saved(output_path)
        return output_path


async def run_download_then_summarize(
    *,
    workers: Optional[int] = None,
    auto_summarize: bool = True,
    skip_summarize_prompt: bool = False,
    log: LogFn = _default_log,
) -> Optional[Path]:
    await run_download(workers=workers, log=log)
    if not auto_summarize:
        return None
    # 用户已选择「下载并汇总」，跳过重复的「确认汇总」弹窗
    return run_summarize(skip_prompt=True, log=log)


def run_download_then_summarize_sync(**kwargs) -> Optional[Path]:
    return asyncio.run(run_download_then_summarize(**kwargs))
