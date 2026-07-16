"""网页版后端：与桌面 GUI 共用 pipeline，提供 REST + SSE。"""
from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
import webbrowser
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.app_config import AppConfig
from config.config_registry import all_config_files
from config.download_settings import DownloadConfig
from config.menu_schema import APP_MENU
from config.settings import DOC_URLS_PATH, apply_app_config
from config.summarize_settings import SummarizeConfig
from config.voice_actor_pricing import load_config as load_pricing_config
from config.voice_actor_pricing import save_config as save_pricing_config
from config.voice_actor_pricing import validate_config as validate_pricing_config


def _resolve_static_dir() -> Path:
    from config.frozen_bootstrap import is_frozen
    from config.runtime_paths import get_base_dir

    bundled = Path(__file__).resolve().parent / "static"
    if is_frozen():
        external = get_base_dir() / "web" / "static"
        if external.is_dir():
            return external
    return bundled


STATIC_DIR = _resolve_static_dir()


class SummarizeTaskRequest(BaseModel):
    sheet_name: Optional[str] = None
    date_ranges: List[List[str]] = []


class ConfigSaveRequest(BaseModel):
    data: Any


class TaskRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._status = "就绪"
        self._detail = "等待操作"
        self._last_output: Optional[str] = None
        self._worker: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "status": self._status,
                "detail": self._detail,
                "last_output": self._last_output,
            }

    def _set_status(self, title: str, detail: str = "") -> None:
        with self._lock:
            self._status = title
            self._detail = detail

    def _log(self, msg: str) -> None:
        self._log_queue.put(msg)
        stripped = msg.strip()
        if stripped and not stripped.startswith("="):
            self._set_status(stripped[:40], stripped)

    def _begin(self) -> None:
        with self._lock:
            if self._running:
                raise RuntimeError("当前有任务正在运行，请稍候")
            self._running = True
        self._log("—— 任务开始 ——")

    def _end(self) -> None:
        with self._lock:
            self._running = False

    def run_download(self, workers: Optional[int] = None) -> None:
        self._begin()
        self._set_status("下载", "批量拉取腾讯文档…")

        def work() -> None:
            from core.pipeline import run_download_sync

            try:
                run_download_sync(workers=workers, log=self._log)
                self._set_status("下载完成", "就绪")
                self._log("—— 下载完成 ——")
            except Exception as exc:
                self._set_status("下载失败", str(exc))
                self._log(f"[错误] {exc}")
            finally:
                self._end()

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _run_summarize_core(self, payload: SummarizeTaskRequest) -> None:
        from core.pipeline import run_summarize_core

        apply_app_config()
        config = SummarizeConfig.load()
        if payload.sheet_name:
            config = replace(config, sheet_name=payload.sheet_name.strip() or None)

        ranges = []
        for item in payload.date_ranges:
            if len(item) >= 2:
                ranges.append((date.fromisoformat(item[0]), date.fromisoformat(item[1])))

        saved = run_summarize_core(
            config,
            ranges,
            log=self._log,
            status_fn=lambda m: self._set_status("汇总", m),
        )
        if saved:
            with self._lock:
                self._last_output = str(saved)
            self._set_status("汇总完成", saved.name)
            self._log(f"已保存: {saved}")
        else:
            self._set_status("汇总未完成", "请查看日志")

    def run_summarize(self, payload: SummarizeTaskRequest) -> None:
        self._begin()
        self._set_status("汇总", "准备中…")

        def work() -> None:
            try:
                self._run_summarize_core(payload)
                self._log("—— 汇总结束 ——")
            except Exception as exc:
                self._set_status("汇总失败", str(exc))
                self._log(f"[错误] {exc}")
            finally:
                self._end()

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def run_both(
        self,
        workers: Optional[int] = None,
        sum_payload: Optional[SummarizeTaskRequest] = None,
    ) -> None:
        self._begin()
        self._set_status("下载", "批量拉取腾讯文档…")

        def work() -> None:
            from core.pipeline import run_download_sync

            try:
                run_download_sync(workers=workers, log=self._log)
                self._set_status("下载完成", "即将开始汇总…")
                self._log("—— 下载完成，开始汇总 ——")
                self._run_summarize_core(sum_payload or SummarizeTaskRequest())
            except Exception as exc:
                self._set_status("任务失败", str(exc))
                self._log(f"[错误] {exc}")
            finally:
                self._end()

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def drain_logs(self, timeout: float = 0.5) -> List[str]:
        lines: List[str] = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                lines.append(self._log_queue.get_nowait())
            except queue.Empty:
                break
        return lines


# SSE 活跃客户端跟踪（用来判断所有浏览器标签页是否都已关闭）
_active_sse_clients = 0
_sse_clients_lock = threading.Lock()
_shutdown_event = None  # asyncio.Event，由 run_web_server 创建
_shutdown_timer: Optional[threading.Timer] = None
_GRACE_PERIOD_SEC = 3  # 所有客户端断开后等待 3 秒再退出


def _inc_sse_clients() -> None:
    global _active_sse_clients, _shutdown_timer
    with _sse_clients_lock:
        _active_sse_clients += 1
        # 有客户端连接，取消待执行的退出定时器
        if _shutdown_timer is not None:
            _shutdown_timer.cancel()
            _shutdown_timer = None


def _dec_sse_clients() -> None:
    global _active_sse_clients, _shutdown_timer
    should_shutdown = False
    with _sse_clients_lock:
        _active_sse_clients -= 1
        if _active_sse_clients <= 0 and _shutdown_event is not None:
            # 所有客户端都断开了，启动一个定时器等待优雅关闭
            if _shutdown_timer is None:
                def _do_shutdown() -> None:
                    if _shutdown_event is not None:
                        _shutdown_event.set()
                _shutdown_timer = threading.Timer(_GRACE_PERIOD_SEC, _do_shutdown)
                _shutdown_timer.daemon = True
                _shutdown_timer.start()


runner = TaskRunner()
web_app = FastAPI(title="录音师工单自动化")
app = web_app


@web_app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@web_app.on_event("shutdown")
async def _cleanup_shutdown_timer() -> None:
    global _shutdown_timer
    if _shutdown_timer is not None:
        _shutdown_timer.cancel()
        _shutdown_timer = None


@web_app.get("/api/menu")
async def get_menu() -> List[Dict[str, Any]]:
    out = []
    for l1 in APP_MENU:
        out.append(
            {
                "key": l1.key,
                "title": l1.title,
                "children": [
                    {
                        "key": l2.key,
                        "title": l2.title,
                        "panel": l2.panel,
                        "sections": [s.title for s in l2.sections],
                    }
                    for l2 in l1.children
                ],
            }
        )
    return out


@web_app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    return runner.status()


@web_app.get("/api/logs/stream")
async def log_stream() -> StreamingResponse:
    async def events():
        _inc_sse_clients()
        try:
            while True:
                lines = runner.drain_logs(timeout=0.8)
                for line in lines:
                    yield f"data: {json.dumps({'line': line}, ensure_ascii=False)}\n\n"
                st = runner.status()
                yield f"data: {json.dumps({'status': st}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.4)
        finally:
            _dec_sse_clients()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@web_app.post("/api/shutdown")
async def api_shutdown() -> Dict[str, str]:
    """前端页面关闭时调用，触发程序退出。"""
    if _shutdown_event is not None:
        _shutdown_event.set()
    return {"ok": "shutting_down"}


@web_app.get("/api/config/files")
async def config_files() -> List[Dict[str, Any]]:
    return [
        {
            "key": e.key,
            "title": e.title,
            "path": str(e.path.resolve()),
            "description": e.description,
            "editable": e.editable_in_ui,
        }
        for e in all_config_files()
    ]


@web_app.get("/api/config/{name}")
async def get_config(name: str) -> Any:
    apply_app_config()
    if name == "app":
        return asdict(AppConfig.load())
    if name == "download":
        return asdict(DownloadConfig.load())
    if name == "summarize":
        cfg = SummarizeConfig.load()
        return {
            "prompt_before_summarize": cfg.prompt_before_summarize,
            "auto_summarize_after_download": cfg.auto_summarize_after_download,
            "prompt_for_sheet_name": cfg.prompt_for_sheet_name,
            "prompt_for_date_ranges": cfg.prompt_for_date_ranges,
            "sheet_name": cfg.sheet_name or "",
            "output_filename_prefix": cfg.output_filename_prefix,
            "sample_file_keyword": cfg.sample_file_keyword,
        }
    if name == "pricing":
        return load_pricing_config()
    if name == "docs":
        with open(DOC_URLS_PATH, encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(404, f"未知配置: {name}")


@web_app.post("/api/config/{name}")
async def save_config_api(name: str, body: ConfigSaveRequest) -> Dict[str, str]:
    apply_app_config()
    data = body.data
    if name == "app":
        known = {k for k in AppConfig.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known}
        if "browser_channel" in filtered and filtered["browser_channel"] == "":
            filtered["browser_channel"] = None
        cfg = AppConfig(**filtered)
        cfg.save()
        apply_app_config()
    elif name == "download":
        cfg = DownloadConfig(concurrency=max(1, int(data.get("concurrency", 5))))
        cfg.save()
    elif name == "summarize":
        from config.summarize_settings import SUMMARIZE_CONFIG_PATH

        SUMMARIZE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SUMMARIZE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif name == "pricing":
        validate_pricing_config(data)
        save_pricing_config(data)
    elif name == "docs":
        if not isinstance(data, list):
            raise HTTPException(400, "doc_urls.json 必须是数组")
        with open(DOC_URLS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        raise HTTPException(404, f"未知配置: {name}")
    return {"ok": "saved"}


@web_app.get("/api/summarize/prep")
async def summarize_prep() -> Dict[str, Any]:
    from summarize.aggregator import list_downloaded_xlsx
    from summarize.sheet_selector import find_sample_xlsx, list_sheet_names
    import config.settings as settings_module

    apply_app_config()
    cfg = SummarizeConfig.load()

    # 必须在 apply_app_config() 之后读取 DOWNLOAD_DIR，才能获取用户配置的实际路径
    search_dir = Path(settings_module.DOWNLOAD_DIR)
    runner._log(f"[汇总准备] 搜索目录: {search_dir}")

    # 使用 find_sample_xlsx 根据关键字查找样例文件
    # 关键字作用：在下载目录中优先选择文件名包含该关键词的 xlsx 来读取子表名
    sample = find_sample_xlsx(
        search_dir,
        prefer_name_contains=cfg.sample_file_keyword,
        output_prefix=cfg.output_filename_prefix,
    )
    if sample:
        runner._log(f"[汇总准备] 样例文件: {sample.name}")
    else:
        runner._log(f"[汇总准备] 目录是否存在: {search_dir.is_dir()}")

    sheets: List[str] = []
    sample_name = None

    # 优先使用已下载的文件获取 sheet 名
    if sample and sample.is_file():
        sheets = list_sheet_names(sample)
        sample_name = sample.name
        runner._log(f"[汇总准备] 使用已下载文件: {sample_name}, sheet 名: {sheets}")
        if not sheets:
            runner._log(f"[汇总准备] 警告: 文件 {sample_name} 的 sheet 名为空，可能文件格式异常")
    else:
        # 没有已下载文件时，使用探针表下载并读取 sheet 名
        runner._log("[汇总准备] 未找到已下载文件，尝试使用探针表获取工作表名")
        try:
            probe_sheets = await _probe_sheet_names_async()
            if probe_sheets:
                sheets = probe_sheets
                sample_name = "探针表"
                runner._log(f"[汇总准备] 探针表 sheet 名: {sheets}")
            else:
                runner._log("[汇总准备] 探针表获取 sheet 名失败")
        except Exception as exc:
            runner._log(f"[汇总准备] 探针表异常: {exc}")

    return {
        "config": {
            "prompt_before_summarize": cfg.prompt_before_summarize,
            "prompt_for_sheet_name": cfg.prompt_for_sheet_name,
            "prompt_for_date_ranges": cfg.prompt_for_date_ranges,
            "sheet_name": cfg.sheet_name or "",
        },
        "sample_file": sample_name,
        "sheets": sheets,
    }


async def _probe_sheet_names_async() -> List[str]:
    """使用 Playwright 下载探针表并读取其 sheet 名列表。"""
    import tempfile
    import shutil
    from pages.sheet_page import SheetPage
    from config.settings import PROBE_SHEET_URL, STORAGE_STATE_PATH
    from playwright.async_api import async_playwright

    probe_url = PROBE_SHEET_URL.strip()
    if not probe_url:
        return []

    tmp_dir = tempfile.mkdtemp(prefix="tencent_probe_sheets_")
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context_kwargs = {"accept_downloads": True}
            if STORAGE_STATE_PATH and Path(STORAGE_STATE_PATH).is_file():
                context_kwargs["storage_state"] = str(STORAGE_STATE_PATH)
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            try:
                sheet_page = SheetPage(page)
                ok = await sheet_page.probe_download(
                    probe_url, tmp_dir, timeout_sec=20, label="获取工作表名"
                )
                if ok:
                    probe_files = sorted(Path(tmp_dir).glob("*.xlsx"))
                    if probe_files:
                        from summarize.sheet_selector import list_sheet_names
                        names = list_sheet_names(probe_files[0])
                        return names
                return []
            except Exception as exc:
                print(f"探针读取 sheet 名异常: {exc}")
                return []
            finally:
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await context.close()
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass
    except Exception as exc:
        print(f"Playwright 启动失败: {exc}")
        return []
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@web_app.post("/api/tasks/download")
async def task_download(workers: Optional[int] = None) -> Dict[str, str]:
    try:
        runner.run_download(workers=workers)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": "started"}


@web_app.post("/api/tasks/summarize")
async def task_summarize(body: SummarizeTaskRequest = Body(default_factory=SummarizeTaskRequest)) -> Dict[str, str]:
    try:
        runner.run_summarize(body)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": "started"}


@web_app.post("/api/tasks/both")
async def task_both(
    workers: Optional[int] = None,
    body: SummarizeTaskRequest = Body(default_factory=SummarizeTaskRequest),
) -> Dict[str, str]:
    try:
        runner.run_both(workers=workers, sum_payload=body)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": "started"}


web_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def run_web_server(*, host: str = "0.0.0.0", port: int = 8765) -> None:
    import uvicorn
    import signal

    from web.network import browser_open_url, list_access_urls, resolve_bind_host

    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # 绑定到 0.0.0.0 自动使局域网可访问
    bind_host = resolve_bind_host(host)
    urls = list_access_urls(port, bind_host=bind_host)
    local_url = browser_open_url(port)
    lan_urls = [u for u in urls if "127.0.0.1" not in u and "localhost" not in u]

    # 同时将启动日志推送到 SSE 日志流，让网页端也能看到
    startup_lines = [
        "=" * 50,
        "网页版已启动",
        f"本机访问: {local_url}",
    ]
    if bind_host == "0.0.0.0" and lan_urls:
        startup_lines.append("局域网访问（其他电脑浏览器打开以下地址）:")
        for u in lan_urls:
            startup_lines.append(f"  {u}")
    elif bind_host == "127.0.0.1":
        startup_lines.append("当前仅本机可访问（web_host=127.0.0.1）")
        startup_lines.append("若需局域网访问，请在配置中将 web_host 改为 0.0.0.0")
    startup_lines.append("（关闭浏览器窗口或所有标签页后，本程序将自动退出）")
    if bind_host == "0.0.0.0":
        startup_lines.append(f"提示: 若局域网无法访问，请在防火墙中放行 TCP 端口 {port}")
    startup_lines.append("=" * 50)

    for line in startup_lines:
        print(line)
        runner._log(line)
    try:
        webbrowser.open(local_url)
    except Exception:
        pass

    config = uvicorn.Config(web_app, host=bind_host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    async def _wait_shutdown() -> None:
        await _shutdown_event.wait()
        print("\n检测到浏览器已关闭，正在停止服务…")
        server.should_exit = True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            asyncio.gather(
                server.serve(),
                _wait_shutdown(),
            )
        )
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        _shutdown_event = None
