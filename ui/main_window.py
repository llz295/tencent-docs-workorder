"""主界面：一二三级菜单 + 配置面板 + 任务执行。"""
from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Dict, Optional

import customtkinter as ctk

from config.app_config import AppConfig
from config.voice_actor_pricing import (
    config_path as pricing_config_path,
    load_config as load_pricing_config,
    reload_app_pricing,
    save_config as save_pricing_config,
    validate_config as validate_pricing_config,
)
from config.download_settings import DOWNLOAD_CONFIG_PATH, DownloadConfig
from config.settings import DOC_URLS_PATH, apply_app_config
from config.summarize_settings import SUMMARIZE_CONFIG_PATH, SummarizeConfig
from core.pipeline import (
    prepare_summarize,
    run_download_sync,
    run_summarize_core,
)
from ui.config_registry import all_config_files, data_directory
from ui.file_ops import (
    open_file_with_default_app,
    open_path_in_explorer,
    read_text_file,
    write_text_file,
)
from ui.menu_schema import APP_MENU, find_level2

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ACCENT = "#1a5fb4"
SIDEBAR_BG = "#0d1b2a"
SIDEBAR_FG = "#e0e6ed"
SIDEBAR_MUTED = "#778da9"
CARD_BG = "#f8fafc"
BORDER = "#cbd5e1"


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("腾讯文档 · 录音师工单自动化")
        self.geometry("1180x760")
        self.minsize(960, 640)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._panels: Dict[str, ctk.CTkFrame] = {}
        self._menu_buttons: Dict[str, ctk.CTkButton] = {}
        self._active_l2: Optional[str] = None
        self._task_running = False
        self._progress_pulse: Optional[str] = None
        self._json_editors: Dict[str, ctk.CTkTextbox] = {}
        self._last_saved_path: Optional[Path] = None

        self._app_cfg = AppConfig.load()
        self._dl_cfg = DownloadConfig.load()
        self._sum_cfg = SummarizeConfig.load()

        self._build_layout()
        self._select_menu("workbench.run")
        self.after(120, self._drain_log_queue)

    # ── layout ──────────────────────────────────────────────

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=SIDEBAR_BG)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        brand = ctk.CTkLabel(
            sidebar,
            text="录音师工单\n自动化平台",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
            justify="left",
        )
        brand.pack(anchor="w", padx=20, pady=(24, 8))

        sub = ctk.CTkLabel(
            sidebar,
            text="腾讯文档 POM",
            font=ctk.CTkFont(size=12),
            text_color=SIDEBAR_MUTED,
        )
        sub.pack(anchor="w", padx=20, pady=(0, 16))

        nav = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        nav.pack(fill="both", expand=True, padx=8, pady=4)

        for l1 in APP_MENU:
            ctk.CTkLabel(
                nav,
                text=l1.title,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=SIDEBAR_MUTED,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(14, 4))

            for l2 in l1.children:
                btn = ctk.CTkButton(
                    nav,
                    text=f"  {l2.title}",
                    anchor="w",
                    height=34,
                    fg_color="transparent",
                    text_color=SIDEBAR_FG,
                    hover_color="#1b263b",
                    font=ctk.CTkFont(size=13),
                    command=lambda k=l2.key: self._select_menu(k),
                )
                btn.pack(fill="x", padx=8, pady=2)
                self._menu_buttons[l2.key] = btn

        content_wrap = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0)
        content_wrap.grid(row=0, column=1, sticky="nsew")
        content_wrap.grid_columnconfigure(0, weight=1)
        content_wrap.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(content_wrap, fg_color="white", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self._hdr_title = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#0f172a",
        )
        self._hdr_title.grid(row=0, column=0, sticky="w", padx=28, pady=(18, 4))

        self._hdr_breadcrumb = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#64748b",
        )
        self._hdr_breadcrumb.grid(row=1, column=0, sticky="w", padx=28, pady=(0, 14))

        self._content = ctk.CTkScrollableFrame(
            content_wrap, fg_color=CARD_BG, corner_radius=0
        )
        self._content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        status = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#e2e8f0")
        status.grid(row=1, column=0, columnspan=2, sticky="ew")
        status.grid_columnconfigure(1, weight=1)

        self._status_dot = ctk.CTkLabel(
            status, text="●", width=20, text_color="#22c55e", font=ctk.CTkFont(size=14)
        )
        self._status_dot.grid(row=0, column=0, rowspan=2, padx=(16, 4), pady=8)

        self._status = ctk.CTkLabel(
            status,
            text="就绪",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#0f172a",
        )
        self._status.grid(row=0, column=1, sticky="w", pady=(8, 0))

        self._status_detail = ctk.CTkLabel(
            status,
            text="等待操作",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self._status_detail.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        self._progress = ctk.CTkProgressBar(
            status, width=140, height=8, progress_color=ACCENT
        )
        self._progress.grid(row=0, column=2, rowspan=2, padx=16, pady=12)
        self._progress.set(0)

        self._build_all_panels()

    def _build_all_panels(self) -> None:
        builders: Dict[str, Callable[[], None]] = {
            "dashboard": self._panel_dashboard,
            "download": self._panel_download,
            "download_browser": self._panel_download_browser,
            "summarize": self._panel_summarize,
            "summarize_output": self._panel_summarize_output,
            "pricing": self._panel_pricing,
            "paths": self._panel_paths,
            "paths_login": self._panel_paths_login,
            "docs": self._panel_docs,
            "advanced": self._panel_advanced,
            "config_files": self._panel_config_files,
            "log": self._panel_log,
        }
        for name, fn in builders.items():
            frame = ctk.CTkFrame(self._content, fg_color="transparent")
            fn(frame)
            self._panels[name] = frame

    def _show_panel(self, name: str) -> None:
        for key, frame in self._panels.items():
            if key == name:
                frame.pack(fill="both", expand=True, padx=24, pady=16)
            else:
                frame.pack_forget()

    def _select_menu(self, l2_key: str) -> None:
        item = find_level2(l2_key)
        if not item:
            return
        self._active_l2 = l2_key
        for key, btn in self._menu_buttons.items():
            if key == l2_key:
                btn.configure(fg_color=ACCENT, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=SIDEBAR_FG)

        l1_title = next(l1.title for l1 in APP_MENU if any(c.key == l2_key for c in l1.children))
        l3 = " · ".join(s.title for s in item.sections) if item.sections else ""
        self._hdr_title.configure(text=item.title)
        self._hdr_breadcrumb.configure(text=f"{l1_title}  /  {item.title}  /  {l3}")
        self._show_panel(item.panel)

    # ── widgets helpers ─────────────────────────────────────

    @staticmethod
    def _section(parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        box = ctk.CTkFrame(
            parent,
            fg_color="white",
            corner_radius=12,
            border_width=1,
            border_color=BORDER,
        )
        box.pack(fill="x", pady=8)
        ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#0f172a",
        ).pack(anchor="w", padx=20, pady=(16, 8))
        body = ctk.CTkFrame(box, fg_color="transparent")
        body.pack(fill="x", padx=20, pady=(0, 16))
        return body

    def _config_paths_banner(
        self,
        parent: ctk.CTkFrame,
        files: list[tuple[str, Path]],
        *,
        folder_only: bool = False,
    ) -> None:
        """顶部展示配置文件完整路径，并可打开文件 / 打开所在文件夹。"""
        box = ctk.CTkFrame(
            parent,
            fg_color="#eff6ff",
            corner_radius=10,
            border_width=1,
            border_color="#93c5fd",
        )
        box.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            box,
            text="本页关联的配置文件",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1e3a5f",
        ).pack(anchor="w", padx=16, pady=(12, 6))

        for label, path in files:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=140,
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#334155",
            ).pack(side="left", anchor="n")
            path_lbl = ctk.CTkLabel(
                row,
                text=str(path.resolve()),
                anchor="w",
                justify="left",
                wraplength=520,
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color="#475569",
            )
            path_lbl.pack(side="left", fill="x", expand=True, padx=(4, 8))
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right")
            is_dir = path.is_dir() or folder_only
            if not is_dir:
                ctk.CTkButton(
                    btn_frame,
                    text="打开文件",
                    width=88,
                    height=28,
                    fg_color=ACCENT,
                    command=lambda p=path: open_file_with_default_app(p),
                ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_frame,
                text="打开文件夹",
                width=96,
                height=28,
                fg_color="#64748b",
                command=lambda p=path: open_path_in_explorer(p),
            ).pack(side="left", padx=2)

        ctk.CTkLabel(box, text="").pack(pady=4)

    def _json_editor_block(
        self,
        parent: ctk.CTkFrame,
        path: Path,
        *,
        editor_key: str,
        height: int = 200,
    ) -> None:
        """界面内直接编辑 JSON 文本并保存到磁盘。"""
        box = self._section(parent, f"JSON 原文编辑 · {path.name}")
        path_var = tk.StringVar(value=str(path.resolve()))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row, text="文件路径:", width=80, anchor="w").pack(side="left")
        ctk.CTkEntry(row, textvariable=path_var, width=480, state="readonly").pack(
            side="left", padx=6
        )

        tb = ctk.CTkTextbox(
            box,
            width=680,
            height=height,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        tb.pack(fill="both", expand=True, pady=6)
        tb.insert("1.0", read_text_file(path))
        self._json_editors[str(path.resolve())] = tb

        bar = ctk.CTkFrame(box, fg_color="transparent")
        bar.pack(fill="x", pady=4)

        def reload_from_disk() -> None:
            tb.delete("1.0", "end")
            tb.insert("1.0", read_text_file(path))
            self._set_status(f"已加载 {path.name}")

        def save_to_disk() -> None:
            try:
                raw = tb.get("1.0", "end").strip()
                json.loads(raw)
            except json.JSONDecodeError as exc:
                messagebox.showerror("JSON 格式错误", str(exc))
                return
            write_text_file(path, raw + "\n")
            self._reload_configs(silent=True)
            messagebox.showinfo("保存", f"已写入:\n{path}")

        ctk.CTkButton(
            bar, text="从磁盘重新加载", width=120, command=reload_from_disk
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bar,
            text="保存到文件",
            width=100,
            fg_color=ACCENT,
            command=save_to_disk,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bar,
            text="用默认程序打开",
            width=120,
            fg_color="#64748b",
            command=lambda: open_file_with_default_app(path),
        ).pack(side="left", padx=4)

    def _row_switch(self, parent, label: str, variable: tk.BooleanVar) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=220, anchor="w").pack(side="left")
        ctk.CTkSwitch(row, variable=variable, text="").pack(side="right")

    def _row_entry(self, parent, label: str, variable: tk.StringVar, *, width: int = 360) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=220, anchor="w").pack(side="left")
        ctk.CTkEntry(row, textvariable=variable, width=width).pack(side="left", padx=(8, 0))

    def _row_spin(self, parent, label: str, variable: tk.IntVar, *, from_: int, to: int) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=220, anchor="w").pack(side="left")
        ctk.CTkSlider(
            row,
            from_=from_,
            to=to,
            number_of_steps=to - from_,
            variable=variable,
            width=220,
            command=lambda v: variable.set(int(float(v))),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row, textvariable=variable, width=40).pack(side="left", padx=8)

    def _save_bar(self, parent, on_save: Callable[[], None]) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=16)
        ctk.CTkButton(
            bar,
            text="保存本页配置",
            fg_color=ACCENT,
            hover_color="#164a8f",
            command=on_save,
        ).pack(side="left")
        ctk.CTkButton(
            bar,
            text="重新加载",
            fg_color="#94a3b8",
            hover_color="#64748b",
            command=self._reload_configs,
        ).pack(side="left", padx=12)

    def _reload_configs(self, *, silent: bool = False) -> None:
        apply_app_config()
        self._app_cfg = AppConfig.load()
        self._dl_cfg = DownloadConfig.load()
        self._sum_cfg = SummarizeConfig.load()
        self._refresh_active_panel_fields()
        for path_str, tb in self._json_editors.items():
            p = Path(path_str)
            tb.delete("1.0", "end")
            tb.insert("1.0", read_text_file(p))
        if hasattr(self, "_docs_text"):
            self._docs_text.delete("1.0", "end")
            if DOC_URLS_PATH.is_file():
                self._docs_text.insert("1.0", read_text_file(DOC_URLS_PATH))
        self._set_status("配置已重新加载")
        if not silent:
            messagebox.showinfo("配置", "已从配置文件重新加载（表单与 JSON 编辑器已刷新）。")

    def _refresh_active_panel_fields(self) -> None:
        """把磁盘配置同步到当前页表单控件。"""
        if not self._active_l2:
            return
        item = find_level2(self._active_l2)
        if not item:
            return
        panel = item.panel
        if panel == "download" and hasattr(self, "_var_concurrency"):
            self._var_concurrency.set(self._dl_cfg.concurrency)
            self._var_retry.set(self._app_cfg.retry_round_delay_sec)
        elif panel == "download_browser" and hasattr(self, "_var_headless"):
            self._var_headless.set(self._app_cfg.headless)
            self._var_channel.set(self._app_cfg.browser_channel or "")
        elif panel == "summarize" and hasattr(self, "_var_prompt_sum"):
            self._var_prompt_sum.set(self._sum_cfg.prompt_before_summarize)
            self._var_auto_sum.set(self._sum_cfg.auto_summarize_after_download)
            self._var_prompt_sheet.set(self._sum_cfg.prompt_for_sheet_name)
            self._var_prompt_date.set(self._sum_cfg.prompt_for_date_ranges)
        elif panel == "summarize_output" and hasattr(self, "_var_prefix"):
            self._var_prefix.set(self._sum_cfg.output_filename_prefix)
            self._var_sheet.set(self._sum_cfg.sheet_name or "")
            self._var_sample_kw.set(self._sum_cfg.sample_file_keyword)
        elif panel == "paths" and hasattr(self, "_var_dl_dir"):
            self._var_dl_dir.set(str(self._app_cfg.download_path()))
            self._var_out_dir.set(str(self._app_cfg.output_path()))
        elif panel == "paths_login" and hasattr(self, "_var_probe"):
            self._var_probe.set(self._app_cfg.probe_sheet_url)
            self._var_login_to.set(self._app_cfg.login_wait_timeout_sec)
            if hasattr(self, "_var_probe_wait"):
                self._var_probe_wait.set(getattr(self._app_cfg, "probe_wait_sec", 20))
            if hasattr(self, "_var_ui_mode"):
                self._var_ui_mode.set(getattr(self._app_cfg, "ui_mode", "ask"))
                self._var_web_host.set(getattr(self._app_cfg, "web_host", "0.0.0.0"))
                self._var_web_port.set(getattr(self._app_cfg, "web_port", 8765))
        elif panel == "advanced" and hasattr(self, "_var_editor_to"):
            self._var_editor_to.set(self._app_cfg.editor_ready_timeout_ms)
            self._var_menu_to.set(self._app_cfg.menu_ready_timeout_ms)
            self._var_sheet_wait.set(self._app_cfg.sheet_load_wait_ms)

    def _set_status(self, text: str, *, detail: str = "") -> None:
        self._status.configure(text=text)
        if detail:
            self._status_detail.configure(text=detail)

    def _set_task_status(self, title: str, detail: str) -> None:
        """更新状态栏主/副标题（可从工作线程经 after 调用）。"""
        self._status.configure(text=title)
        self._status_detail.configure(text=detail)

    @staticmethod
    def _phase_title_for_status(msg: str) -> str:
        """把流水线状态文案映射为状态栏主标题。"""
        if "完成" in msg and ("汇总" in msg or ".xlsx" in msg):
            return "汇总完成"
        if "错误" in msg or msg.startswith("[!]"):
            return "汇总失败"
        if "读取工单" in msg or "已合并" in msg or "[OK]" in msg:
            return "读取工单"
        if "生成主表" in msg or "分段主表" in msg or "写入" in msg:
            return "写入 Excel"
        if "准备" in msg or "确认" in msg or "选择" in msg:
            return "汇总准备"
        if "下载" in msg:
            return "下载"
        return "汇总"

    @staticmethod
    def _short_detail(msg: str, *, limit: int = 80) -> str:
        msg = msg.replace("\n", " ").strip()
        if len(msg) <= limit:
            return msg
        return msg[: limit - 1] + "…"

    def _task_progress_from_thread(self, msg: str) -> None:
        """工作线程：同步更新状态栏主标题 + 副标题。"""
        title = self._phase_title_for_status(msg)
        detail = self._short_detail(msg)

        def apply() -> None:
            if not self.winfo_exists():
                return
            self._status.configure(text=title)
            self._status_detail.configure(text=detail)

        if threading.current_thread() is threading.main_thread():
            apply()
            self.update_idletasks()
        else:
            self.after(0, apply)

    def _show_saved_result(self, path: Path) -> None:
        """在运行日志页顶部展示最近一次保存路径。"""
        self._last_saved_path = path
        if not hasattr(self, "_result_banner"):
            return
        self._result_path_lbl.configure(text=str(path))

    def _start_progress_pulse(self) -> None:
        self._task_running = True
        self._status_dot.configure(text_color=ACCENT)
        self._pulse_progress(0.0, 1)

    def _stop_progress_pulse(self, *, success: bool = True) -> None:
        self._task_running = False
        if self._progress_pulse:
            self.after_cancel(self._progress_pulse)
            self._progress_pulse = None
        self._progress.set(1 if success else 0)
        self._status_dot.configure(text_color="#22c55e" if success else "#ef4444")

    def _pulse_progress(self, value: float, direction: int) -> None:
        if not self._task_running:
            return
        try:
            if not self.winfo_exists():
                return
            v = value + direction * 0.08
            if v >= 0.95:
                v, direction = 0.95, -1
            elif v <= 0.05:
                v, direction = 0.05, 1
            self._progress.set(v)
            self._progress_pulse = self.after(
                80, lambda: self._pulse_progress(v, direction)
            )
        except tk.TclError:
            self._progress_pulse = None

    def _focus_log_panel(self) -> None:
        """切换到运行日志页，便于查看实时输出。"""
        self._select_menu("system.log")
        self._append_log("—— 任务开始 ——")

    def _append_log(self, line: str) -> None:
        if hasattr(self, "_log_box"):
            self._log_box.configure(state="normal")
            self._log_box.insert("end", line + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")

    def _drain_log_queue(self) -> None:
        try:
            if not self.winfo_exists():
                return
            while True:
                try:
                    line = self._log_queue.get_nowait()
                except queue.Empty:
                    break
                self._append_log(line)
        except tk.TclError:
            return
        self.after(120, self._drain_log_queue)

    def _log_fn(self, msg: str) -> None:
        self._log_queue.put(msg)
        stripped = msg.strip()
        if not stripped or stripped.startswith("="):
            return
        # 与 status_fn 相同规则：日志里的进度也驱动状态栏
        if any(
            k in stripped
            for k in (
                "读取",
                "合并",
                "生成",
                "汇总",
                "完成",
                "错误",
                "工单",
                "保存",
                "开始",
                "重试",
                "写入",
                "[OK]",
                "[!]",
            )
        ):
            self._task_progress_from_thread(stripped)

    def _run_task(self, target: Callable[[], None], *, busy: str) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("忙碌", "当前有任务正在运行，请稍候。")
            return

        def wrapper() -> None:
            try:
                target()
                self.after(0, lambda: self._on_task_finished("任务完成", "就绪"))
            except Exception as exc:
                err_msg = str(exc)
                self._log_fn(f"[错误] {err_msg}")
                self.after(
                    0,
                    lambda m=err_msg: self._on_task_finished("任务失败", m, success=False),
                )
            finally:
                self.after(0, lambda: self._set_buttons_enabled(True))

        self._set_buttons_enabled(False)
        self._set_task_status(busy, "任务执行中…")
        self._start_progress_pulse()
        self._worker = threading.Thread(target=wrapper, daemon=True)
        self._worker.start()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for attr in ("_btn_dl", "_btn_sum", "_btn_both"):
            if hasattr(self, attr):
                getattr(self, attr).configure(state=state)

    def _needs_summarize_ui(self) -> bool:
        cfg = SummarizeConfig.load()
        return bool(
            cfg.prompt_before_summarize
            or cfg.prompt_for_sheet_name
            or (cfg.prompt_for_date_ranges and not (cfg.sheet_name or "").strip())
        )

    def _on_task_finished(
        self, title: str, detail: str, *, success: bool = True
    ) -> None:
        self._stop_progress_pulse(success=success)
        self._set_task_status(title, detail)

    def _on_summarize_done(self, saved: Optional[Path], *, cancelled: bool = False) -> None:
        self._set_buttons_enabled(True)
        self._stop_progress_pulse(success=saved is not None and not cancelled)
        if cancelled:
            self._set_task_status("汇总已取消", "等待操作")
            self._append_log("—— 汇总未执行 ——")
            return
        if saved is None:
            self._set_task_status("汇总未完成", "请查看运行日志中的错误信息")
            return
        path = Path(saved)
        self._show_saved_result(path)
        self._set_task_status("汇总完成", path.name)
        self._status_detail.configure(text=str(path))
        self._append_log("—— 汇总完成 ——")
        self._append_log(f"已保存: {path}")
        self._focus_log_panel()
        if messagebox.askyesno(
            "汇总完成",
            f"已保存到:\n{path}\n\n是否打开所在文件夹？",
            default="yes",
        ):
            open_path_in_explorer(path)

    def _start_summarize(self, *, skip_confirm: bool = False) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("忙碌", "当前有任务正在运行，请稍候。")
            return

        self._set_buttons_enabled(False)
        self._focus_log_panel()
        self._set_task_status("汇总", "准备中（确认选项）…")
        self._log_fn("=" * 50)
        self._log_fn("录音师工单汇总")

        self.update_idletasks()
        prep = prepare_summarize(
            skip_prompt=skip_confirm,
            log=self._log_fn,
            status_fn=self._task_progress_from_thread,
            tk_parent=self,
        )
        if prep is None:
            self._on_summarize_done(None, cancelled=True)
            return

        config, ranges = prep
        self._set_task_status("汇总", "正在读取本地工单并生成 Excel …")
        self._start_progress_pulse()

        def work() -> None:
            saved: Optional[Path] = None
            err: Optional[str] = None
            try:
                saved = run_summarize_core(
                    config,
                    ranges,
                    log=self._log_fn,
                    status_fn=self._task_progress_from_thread,
                )
            except RuntimeError as exc:
                err = str(exc)
                self._log_fn(f"[错误] {err}")
            self.after(
                0,
                lambda: self._on_summarize_done(
                    saved if err is None else None,
                ),
            )

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _start_download_then_summarize(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("忙碌", "当前有任务正在运行，请稍候。")
            return

        def after_download() -> None:
            self._on_task_finished("下载完成", "即将开始汇总…")
            self._start_summarize(skip_confirm=True)

        def work() -> None:
            try:
                run_download_sync(
                    workers=self._dl_cfg.concurrency, log=self._log_fn
                )
            except Exception as exc:
                err_msg = str(exc)
                self._log_fn(f"[错误] {err_msg}")
                self.after(
                    0,
                    lambda m=err_msg: self._on_task_finished("下载失败", m, success=False),
                )
                self.after(0, lambda: self._set_buttons_enabled(True))
                return
            self.after(0, after_download)

        self._set_buttons_enabled(False)
        self._focus_log_panel()
        self._set_task_status("下载", "批量拉取腾讯文档…")
        self._start_progress_pulse()
        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    # ── panels ──────────────────────────────────────────────

    def _panel_dashboard(self, parent: ctk.CTkFrame) -> None:
        cards = ctk.CTkFrame(parent, fg_color="transparent")
        cards.pack(fill="x")

        def card(title: str, desc: str, btn_text: str, cmd, *, attr: str) -> ctk.CTkFrame:
            f = ctk.CTkFrame(cards, fg_color="white", corner_radius=14, border_width=1, border_color=BORDER)
            f.pack(side="left", fill="both", expand=True, padx=8, pady=8)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=17, weight="bold")).pack(
                anchor="w", padx=20, pady=(20, 6)
            )
            ctk.CTkLabel(f, text=desc, text_color="#64748b", wraplength=260, justify="left").pack(
                anchor="w", padx=20
            )
            b = ctk.CTkButton(f, text=btn_text, fg_color=ACCENT, command=cmd)
            b.pack(anchor="w", padx=20, pady=20)
            setattr(self, attr, b)
            return f

        card(
            "批量下载",
            "从腾讯文档拉取全部录音师工单到本地目录。失败自动重试直至成功。",
            "开始下载",
            lambda: self._run_task(
                lambda: run_download_sync(
                    workers=self._dl_cfg.concurrency, log=self._log_fn
                ),
                busy="正在下载…",
            ),
            attr="_btn_dl",
        )
        card(
            "工单汇总",
            "读取本地 Excel，生成主表 / 结算汇总 / 终表，可按时间段加分段主表。",
            "开始汇总",
            self._start_summarize,
            attr="_btn_sum",
        )
        card(
            "下载并汇总",
            "先完成全部下载，再按汇总配置进入汇总流程（可弹窗确认）。",
            "一键执行",
            self._start_download_then_summarize,
            attr="_btn_both",
        )

        hint = ctk.CTkLabel(
            parent,
            text="提示：左侧菜单可修改并发、路径、弹窗行为等；运行日志见「系统 → 运行日志」。",
            text_color="#64748b",
        )
        hint.pack(anchor="w", pady=12)

    def _panel_download(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(
            parent,
            [
                ("下载配置", DOWNLOAD_CONFIG_PATH),
                ("应用配置（重试间隔）", self._app_cfg.path),
            ],
        )
        self._var_concurrency = tk.IntVar(value=self._dl_cfg.concurrency)
        self._var_retry = tk.IntVar(value=self._app_cfg.retry_round_delay_sec)

        s1 = self._section(parent, "表单 · 并发数量")
        self._row_spin(s1, "同时下载文档数", self._var_concurrency, from_=1, to=8)

        s2 = self._section(parent, "表单 · 失败重试")
        self._row_spin(s2, "重试轮次间隔（秒）", self._var_retry, from_=1, to=30)

        self._json_editor_block(parent, DOWNLOAD_CONFIG_PATH, editor_key="dl")
        self._save_bar(parent, self._save_download_page)

    def _save_download_page(self) -> None:
        self._dl_cfg = replace(self._dl_cfg, concurrency=max(1, self._var_concurrency.get()))
        self._dl_cfg.save()
        self._app_cfg.retry_round_delay_sec = max(1, self._var_retry.get())
        self._app_cfg.save()
        apply_app_config()
        self._set_status("下载配置已保存")
        messagebox.showinfo("保存", "下载配置已写入。")

    def _panel_download_browser(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("应用配置", self._app_cfg.path)])
        self._var_headless = tk.BooleanVar(value=self._app_cfg.headless)
        self._var_channel = tk.StringVar(value=self._app_cfg.browser_channel or "")

        s1 = self._section(parent, "表单 · 运行模式")
        self._row_switch(s1, "无头模式（后台下载）", self._var_headless)

        s2 = self._section(parent, "表单 · 浏览器通道")
        self._row_entry(s2, "通道（推荐 chrome）", self._var_channel)
        ctk.CTkLabel(
            s2,
            text="填 chrome = 本机 Google Chrome；留空 = Playwright 自带 Chromium（打包仅含 Chromium）",
            text_color="#64748b",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=4)

        self._json_editor_block(parent, self._app_cfg.path, editor_key="app_br")
        self._save_bar(parent, self._save_browser_page)

    def _save_browser_page(self) -> None:
        ch = self._var_channel.get().strip() or None
        self._app_cfg = replace(
            self._app_cfg,
            headless=bool(self._var_headless.get()),
            browser_channel=ch,
        )
        self._app_cfg.save()
        apply_app_config()
        messagebox.showinfo("保存", "浏览器配置已保存。")

    def _panel_summarize(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("汇总配置", SUMMARIZE_CONFIG_PATH)])
        self._var_prompt_sum = tk.BooleanVar(value=self._sum_cfg.prompt_before_summarize)
        self._var_auto_sum = tk.BooleanVar(value=self._sum_cfg.auto_summarize_after_download)
        self._var_prompt_sheet = tk.BooleanVar(value=self._sum_cfg.prompt_for_sheet_name)
        self._var_prompt_date = tk.BooleanVar(value=self._sum_cfg.prompt_for_date_ranges)

        s1 = self._section(parent, "表单 · 弹窗与确认")
        self._row_switch(s1, "汇总前弹窗确认", self._var_prompt_sum)
        self._row_switch(s1, "下载完成后自动汇总", self._var_auto_sum)

        s2 = self._section(parent, "表单 · 工作表选择")
        self._row_switch(s2, "运行前交互选择 Sheet", self._var_prompt_sheet)

        s3 = self._section(parent, "表单 · 时间段日历")
        self._row_switch(s3, "汇总时弹出日历选段", self._var_prompt_date)

        self._json_editor_block(parent, SUMMARIZE_CONFIG_PATH, editor_key="sum")
        self._save_bar(parent, self._save_summarize_page)

    def _save_summarize_page(self) -> None:
        self._sum_cfg = replace(
            self._sum_cfg,
            prompt_before_summarize=bool(self._var_prompt_sum.get()),
            auto_summarize_after_download=bool(self._var_auto_sum.get()),
            prompt_for_sheet_name=bool(self._var_prompt_sheet.get()),
            prompt_for_date_ranges=bool(self._var_prompt_date.get()),
        )
        self._sum_cfg.save()
        messagebox.showinfo("保存", "汇总流程配置已保存。")

    def _panel_summarize_output(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("汇总配置", SUMMARIZE_CONFIG_PATH)])
        self._var_prefix = tk.StringVar(value=self._sum_cfg.output_filename_prefix)
        self._var_sheet = tk.StringVar(value=self._sum_cfg.sheet_name or "")
        self._var_sample_kw = tk.StringVar(value=self._sum_cfg.sample_file_keyword)

        s1 = self._section(parent, "表单 · 文件名")
        self._row_entry(s1, "输出文件名前缀", self._var_prefix)

        s1b = self._section(parent, "表单 · 样例工单（选 sheet 用）")
        self._row_entry(s1b, "文件名包含关键字", self._var_sample_kw)
        ctk.CTkLabel(
            s1b,
            text="用于读取可选工作表列表，默认「贝儿」对应 1_贝儿-…xlsx",
            text_color="#64748b",
        ).pack(anchor="w", pady=4)

        s2 = self._section(parent, "表单 · 固定工作表")
        self._row_entry(s2, "工作表名（留空=交互或默认）", self._var_sheet)

        self._json_editor_block(parent, SUMMARIZE_CONFIG_PATH, editor_key="sum_out")
        self._save_bar(parent, self._save_summarize_output_page)

    def _save_summarize_output_page(self) -> None:
        sheet = self._var_sheet.get().strip() or None
        self._sum_cfg = replace(
            self._sum_cfg,
            output_filename_prefix=self._var_prefix.get().strip() or "录音师薪资结算结果",
            sheet_name=sheet,
            sample_file_keyword=self._var_sample_kw.get().strip() or "贝儿",
        )
        self._sum_cfg.save()
        messagebox.showinfo("保存", "汇总输出配置已保存。")

    def _panel_pricing(self, parent: ctk.CTkFrame) -> None:
        cfg_path = pricing_config_path()
        self._config_paths_banner(parent, [("价格与映射", cfg_path)])

        ctk.CTkLabel(
            parent,
            text=(
                "汇总时按此表计算「录音价格」：工单里的化名经 name_mapping 转为实名，"
                "再按 prices 中全新(套)/补录(条)单价计算。修改后点保存，再执行汇总验证。"
            ),
            text_color="#64748b",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        s = self._section(parent, "JSON · voice_actor_config.json")
        self._pricing_text = ctk.CTkTextbox(
            s, width=720, height=420, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self._pricing_text.pack(fill="both", expand=True)
        try:
            import json

            self._pricing_text.insert(
                "1.0", json.dumps(load_pricing_config(), ensure_ascii=False, indent=2)
            )
        except Exception as exc:
            self._pricing_text.insert("1.0", f"加载失败: {exc}")

        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=8)
        ctk.CTkButton(
            bar, text="保存到文件", fg_color=ACCENT, command=self._save_pricing
        ).pack(side="left")
        ctk.CTkButton(
            bar,
            text="从磁盘重新加载",
            fg_color="#64748b",
            command=self._reload_pricing_editor,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            bar,
            text="格式化 JSON",
            fg_color="#64748b",
            command=self._format_pricing_json,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            bar,
            text="用默认程序打开",
            fg_color="#64748b",
            command=lambda: open_file_with_default_app(cfg_path),
        ).pack(side="left", padx=8)

    def _reload_pricing_editor(self) -> None:
        import json

        try:
            data = load_pricing_config()
            self._pricing_text.delete("1.0", "end")
            self._pricing_text.insert("1.0", json.dumps(data, ensure_ascii=False, indent=2))
            reload_app_pricing()
            self._set_status("价格表已重新加载")
        except Exception as exc:
            messagebox.showerror("加载失败", str(exc))

    def _format_pricing_json(self) -> None:
        import json

        try:
            data = json.loads(self._pricing_text.get("1.0", "end"))
            validate_pricing_config(data)
            self._pricing_text.delete("1.0", "end")
            self._pricing_text.insert("1.0", json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as exc:
            messagebox.showerror("JSON 错误", str(exc))

    def _save_pricing(self) -> None:
        import json

        raw = self._pricing_text.get("1.0", "end").strip()
        try:
            data = json.loads(raw)
            validate_pricing_config(data)
        except Exception as exc:
            messagebox.showerror("JSON 错误", str(exc))
            return
        try:
            path = save_pricing_config(data)
            reload_app_pricing()
            messagebox.showinfo("保存", f"价格表已写入:\n{path}\n\n汇总时将使用新价格。")
            self._set_status("价格表已保存")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def _panel_paths(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("应用配置", self._app_cfg.path)])
        self._var_dl_dir = tk.StringVar(
            value=str(self._app_cfg.download_path())
        )
        self._var_out_dir = tk.StringVar(
            value=str(self._app_cfg.output_path())
        )

        def pick(var: tk.StringVar) -> None:
            path = filedialog.askdirectory()
            if path:
                var.set(path)

        s1 = self._section(parent, "表单 · 工单下载目录")
        row = ctk.CTkFrame(s1, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkEntry(row, textvariable=self._var_dl_dir, width=420).pack(side="left")
        ctk.CTkButton(row, text="浏览…", width=80, command=lambda: pick(self._var_dl_dir)).pack(
            side="left", padx=8
        )

        s2 = self._section(parent, "表单 · 汇总输出目录")
        row2 = ctk.CTkFrame(s2, fg_color="transparent")
        row2.pack(fill="x", pady=6)
        ctk.CTkEntry(row2, textvariable=self._var_out_dir, width=420).pack(side="left")
        ctk.CTkButton(row2, text="浏览…", width=80, command=lambda: pick(self._var_out_dir)).pack(
            side="left", padx=8
        )

        self._json_editor_block(parent, self._app_cfg.path, editor_key="app_paths")
        self._save_bar(parent, self._save_paths_page)

    def _save_paths_page(self) -> None:
        self._app_cfg.download_dir = self._var_dl_dir.get().strip()
        self._app_cfg.summarize_output_dir = self._var_out_dir.get().strip()
        self._app_cfg.save()
        apply_app_config()
        messagebox.showinfo("保存", "路径配置已保存。")

    def _panel_paths_login(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("应用配置", self._app_cfg.path)])
        self._var_probe = tk.StringVar(value=self._app_cfg.probe_sheet_url)
        self._var_login_to = tk.IntVar(value=self._app_cfg.login_wait_timeout_sec)

        s1 = self._section(parent, "表单 · 探测表格 URL")
        self._row_entry(s1, "登录探测用表格链接", self._var_probe, width=480)

        self._var_probe_wait = tk.IntVar(value=getattr(self._app_cfg, "probe_wait_sec", 20))
        s_probe = self._section(parent, "表单 · 探针等待")
        self._row_spin(s_probe, "探针下载超时（秒，无重试）", self._var_probe_wait, from_=5, to=120)
        ctk.CTkLabel(
            s_probe,
            text="旧会话校验时探针表格须在此时间内下载成功；出现「登录」页会立即判定失效（默认 20 秒）",
            text_color="#64748b",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=4)

        s2 = self._section(parent, "表单 · 扫码超时")
        self._row_spin(s2, "最长等待登录（秒）", self._var_login_to, from_=60, to=600)

        s3 = self._section(parent, "表单 · 启动方式")
        self._var_ui_mode = tk.StringVar(value=getattr(self._app_cfg, "ui_mode", "ask"))
        self._var_web_host = tk.StringVar(value=getattr(self._app_cfg, "web_host", "0.0.0.0"))
        self._var_web_port = tk.IntVar(value=getattr(self._app_cfg, "web_port", 8765))
        row = ctk.CTkFrame(s3, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text="界面模式", width=220, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            row,
            values=["ask", "desktop", "web"],
            variable=self._var_ui_mode,
            width=200,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            s3,
            text="ask=每次询问 | desktop=桌面程序 | web=网页版（二者不可同时运行）",
            text_color="#64748b",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=4)
        self._row_entry(s3, "网页版绑定地址", self._var_web_host, width=160)
        self._row_spin(s3, "网页版端口", self._var_web_port, from_=1024, to=65535)
        ctk.CTkLabel(
            s3,
            text="0.0.0.0 = 允许局域网访问 | 127.0.0.1 = 仅本机；其他电脑用 http://本机局域网IP:端口",
            text_color="#64748b",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=4)

        self._json_editor_block(parent, self._app_cfg.path, editor_key="app_login")
        self._save_bar(parent, self._save_paths_login_page)

    def _save_paths_login_page(self) -> None:
        self._app_cfg.probe_sheet_url = self._var_probe.get().strip()
        self._app_cfg.probe_wait_sec = max(5, min(120, self._var_probe_wait.get()))
        self._app_cfg.login_wait_timeout_sec = max(60, self._var_login_to.get())
        self._app_cfg.ui_mode = self._var_ui_mode.get().strip() or "ask"
        self._app_cfg.web_host = self._var_web_host.get().strip() or "0.0.0.0"
        self._app_cfg.web_port = max(1024, min(65535, self._var_web_port.get()))
        self._app_cfg.save()
        apply_app_config()
        messagebox.showinfo("保存", "登录与启动配置已保存。")

    def _panel_docs(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("文档列表", DOC_URLS_PATH)])
        s = self._section(parent, "表单 · 文档 URL 列表（可直接编辑）")
        self._docs_text = ctk.CTkTextbox(
            s, width=700, height=360, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self._docs_text.pack(fill="both", expand=True)
        self._docs_text.insert("1.0", read_text_file(DOC_URLS_PATH))

        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=8)
        ctk.CTkButton(bar, text="保存到文件", fg_color=ACCENT, command=self._save_docs).pack(
            side="left"
        )
        ctk.CTkButton(
            bar,
            text="从磁盘重新加载",
            fg_color="#64748b",
            command=lambda: (
                self._docs_text.delete("1.0", "end"),
                self._docs_text.insert("1.0", read_text_file(DOC_URLS_PATH)),
            ),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            bar,
            text="用默认程序打开",
            fg_color="#64748b",
            command=lambda: open_file_with_default_app(DOC_URLS_PATH),
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            bar,
            text="格式化 JSON",
            fg_color="#64748b",
            command=self._format_docs_json,
        ).pack(side="left", padx=8)

    def _save_docs(self) -> None:
        raw = self._docs_text.get("1.0", "end").strip()
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("根节点必须是数组")
        except Exception as exc:
            messagebox.showerror("JSON 错误", str(exc))
            return
        DOC_URLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DOC_URLS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("保存", f"已保存 {len(data)} 条文档到 doc_urls.json")

    def _format_docs_json(self) -> None:
        try:
            data = json.loads(self._docs_text.get("1.0", "end"))
            self._docs_text.delete("1.0", "end")
            self._docs_text.insert("1.0", json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as exc:
            messagebox.showerror("JSON 错误", str(exc))

    def _panel_advanced(self, parent: ctk.CTkFrame) -> None:
        self._config_paths_banner(parent, [("应用配置", self._app_cfg.path)])
        self._var_editor_to = tk.IntVar(value=self._app_cfg.editor_ready_timeout_ms)
        self._var_menu_to = tk.IntVar(value=self._app_cfg.menu_ready_timeout_ms)
        self._var_sheet_wait = tk.IntVar(value=self._app_cfg.sheet_load_wait_ms)

        s1 = self._section(parent, "表单 · 编辑器就绪")
        self._row_spin(s1, "超时（毫秒）", self._var_editor_to, from_=5000, to=60000)

        s2 = self._section(parent, "表单 · 菜单就绪")
        self._row_spin(s2, "超时（毫秒）", self._var_menu_to, from_=3000, to=30000)

        s3 = self._section(parent, "表单 · 表格加载")
        self._row_spin(s3, "打开后等待（毫秒）", self._var_sheet_wait, from_=500, to=10000)

        self._json_editor_block(parent, self._app_cfg.path, editor_key="app_adv")
        self._save_bar(parent, self._save_advanced_page)

    def _panel_config_files(self, parent: ctk.CTkFrame) -> None:
        data_dir = data_directory()
        self._config_paths_banner(
            parent,
            [("配置目录", data_dir)],
            folder_only=True,
        )
        ctk.CTkLabel(
            parent,
            text="以下文件均可「打开文件」用记事本 / VS Code 编辑，或在界面内展开 JSON 编辑器。",
            text_color="#64748b",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        for entry in all_config_files():
            box = ctk.CTkFrame(
                parent,
                fg_color="white",
                corner_radius=10,
                border_width=1,
                border_color=BORDER,
            )
            box.pack(fill="x", pady=6)
            head = ctk.CTkFrame(box, fg_color="transparent")
            head.pack(fill="x", padx=16, pady=(12, 4))
            ctk.CTkLabel(
                head,
                text=entry.title,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                head,
                text=entry.description,
                text_color="#64748b",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=12)

            path_row = ctk.CTkFrame(box, fg_color="transparent")
            path_row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(
                path_row,
                text=str(entry.path.resolve()),
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color="#475569",
                wraplength=640,
                justify="left",
            ).pack(side="left", fill="x", expand=True)

            btn_row = ctk.CTkFrame(box, fg_color="transparent")
            btn_row.pack(fill="x", padx=16, pady=(4, 12))
            p = entry.path
            ctk.CTkButton(
                btn_row,
                text="打开文件",
                width=100,
                fg_color=ACCENT,
                command=lambda path=p: open_file_with_default_app(path),
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                btn_row,
                text="打开文件夹",
                width=110,
                fg_color="#64748b",
                command=lambda path=p: open_path_in_explorer(path),
            ).pack(side="left", padx=4)
            if entry.editable_in_ui:
                ctk.CTkButton(
                    btn_row,
                    text="在下方 JSON 区编辑",
                    width=140,
                    fg_color="#0d9488",
                    command=lambda path=p: self._scroll_to_json_editor(path),
                ).pack(side="left", padx=4)

        ctk.CTkLabel(
            parent,
            text="统一 JSON 编辑区（选择文件后加载）",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", pady=(16, 6))

        pick_row = ctk.CTkFrame(parent, fg_color="transparent")
        pick_row.pack(fill="x")
        self._cfg_pick_var = tk.StringVar(
            value=str(all_config_files()[0].path.resolve())
        )
        names = [e.title for e in all_config_files() if e.editable_in_ui]
        self._cfg_pick_map = {
            e.title: e.path for e in all_config_files() if e.editable_in_ui
        }
        menu = ctk.CTkOptionMenu(
            pick_row,
            values=names,
            command=self._on_config_file_picked,
            width=320,
        )
        menu.pack(side="left")
        menu.set(names[0])

        editable = [e for e in all_config_files() if e.editable_in_ui]
        self._master_cfg_path = editable[0].path
        box = self._section(parent, "JSON 编辑区")
        self._master_cfg_tb = ctk.CTkTextbox(
            box,
            width=680,
            height=240,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._master_cfg_tb.pack(fill="both", expand=True, pady=6)
        self._master_cfg_tb.insert("1.0", read_text_file(self._master_cfg_path))
        self._json_editors[str(self._master_cfg_path.resolve())] = self._master_cfg_tb

        mbar = ctk.CTkFrame(box, fg_color="transparent")
        mbar.pack(fill="x", pady=4)

        def reload_master() -> None:
            self._master_cfg_tb.delete("1.0", "end")
            self._master_cfg_tb.insert("1.0", read_text_file(self._master_cfg_path))

        def save_master() -> None:
            try:
                raw = self._master_cfg_tb.get("1.0", "end").strip()
                json.loads(raw)
            except json.JSONDecodeError as exc:
                messagebox.showerror("JSON 格式错误", str(exc))
                return
            write_text_file(self._master_cfg_path, raw + "\n")
            self._reload_configs(silent=True)
            messagebox.showinfo("保存", f"已写入:\n{self._master_cfg_path}")

        ctk.CTkButton(mbar, text="从磁盘重新加载", command=reload_master).pack(
            side="left", padx=4
        )
        ctk.CTkButton(
            mbar, text="保存到当前文件", fg_color=ACCENT, command=save_master
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            mbar,
            text="用默认程序打开",
            fg_color="#64748b",
            command=lambda: open_file_with_default_app(self._master_cfg_path),
        ).pack(side="left", padx=4)

    def _save_advanced_page(self) -> None:
        self._app_cfg.editor_ready_timeout_ms = self._var_editor_to.get()
        self._app_cfg.menu_ready_timeout_ms = self._var_menu_to.get()
        self._app_cfg.sheet_load_wait_ms = self._var_sheet_wait.get()
        self._app_cfg.save()
        apply_app_config()
        messagebox.showinfo("保存", "超时配置已保存。")

    def _on_config_file_picked(self, title: str) -> None:
        path = self._cfg_pick_map.get(title)
        if not path or not hasattr(self, "_master_cfg_tb"):
            return
        self._master_cfg_path = path
        self._master_cfg_tb.delete("1.0", "end")
        self._master_cfg_tb.insert("1.0", read_text_file(path))
        self._set_status(f"已加载 {path.name}")

    def _scroll_to_json_editor(self, path: Path) -> None:
        title = next(
            (e.title for e in all_config_files() if e.path.resolve() == path.resolve()),
            None,
        )
        if title and hasattr(self, "_cfg_pick_map"):
            self._on_config_file_picked(title)
        self._select_menu("system.config_files")

    def _panel_log(self, parent: ctk.CTkFrame) -> None:
        self._result_banner = ctk.CTkFrame(
            parent,
            fg_color="#ecfdf5",
            corner_radius=10,
            border_width=1,
            border_color="#6ee7b7",
        )
        ctk.CTkLabel(
            self._result_banner,
            text="最近一次汇总输出",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#065f46",
        ).pack(anchor="w", padx=16, pady=(12, 4))
        self._result_path_lbl = ctk.CTkLabel(
            self._result_banner,
            text="（汇总完成后将显示完整路径）",
            anchor="w",
            justify="left",
            wraplength=680,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#047857",
        )
        self._result_path_lbl.pack(anchor="w", padx=16, pady=(0, 8))
        rbar = ctk.CTkFrame(self._result_banner, fg_color="transparent")
        rbar.pack(anchor="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            rbar,
            text="打开文件夹",
            width=110,
            fg_color="#059669",
            command=self._open_last_saved_folder,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            rbar,
            text="用 Excel 打开",
            width=110,
            fg_color=ACCENT,
            command=self._open_last_saved_file,
        ).pack(side="left", padx=4)
        self._result_banner.pack(fill="x", padx=0, pady=(0, 8))

        s = self._section(parent, "实时日志")
        self._log_box = ctk.CTkTextbox(
            s, width=720, height=420, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self._log_box.pack(fill="both", expand=True)
        self._log_box.configure(state="disabled")

        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=8)
        ctk.CTkButton(
            bar,
            text="清空日志",
            command=lambda: (
                self._log_box.configure(state="normal"),
                self._log_box.delete("1.0", "end"),
                self._log_box.configure(state="disabled"),
            ),
        ).pack(side="left")

    def _open_last_saved_folder(self) -> None:
        if self._last_saved_path and self._last_saved_path.is_file():
            open_path_in_explorer(self._last_saved_path)
        else:
            messagebox.showinfo("提示", "尚无已保存的汇总文件，请先执行汇总。")

    def _open_last_saved_file(self) -> None:
        if self._last_saved_path and self._last_saved_path.is_file():
            open_file_with_default_app(self._last_saved_path)
        else:
            messagebox.showinfo("提示", "尚无已保存的汇总文件，请先执行汇总。")


def launch() -> None:
    apply_app_config()
    app = MainWindow()
    app.mainloop()
