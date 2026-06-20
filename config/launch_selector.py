"""启动方式选择：桌面 GUI 或网页版（互斥）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config.app_config import AppConfig


def resolve_launch_mode(cfg: AppConfig | None = None) -> str:
    cfg = cfg or AppConfig.load()
    mode = (cfg.ui_mode or "ask").strip().lower()
    if mode in ("desktop", "web"):
        return mode
    return _ask_launch_mode(cfg)


def _ask_launch_mode(cfg: AppConfig) -> str:
    result = {"mode": "desktop", "remember": False}

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    dialog = tk.Toplevel(root)
    dialog.title("选择运行方式")
    dialog.attributes("-topmost", True)
    dialog.resizable(False, False)
    dialog.grab_set()

    ttk.Label(
        dialog,
        text="请选择界面方式（桌面程序与网页版只能运行一种）：",
        padding=(20, 16, 20, 8),
    ).pack()

    var_mode = tk.StringVar(value="desktop")
    var_remember = tk.BooleanVar(value=False)

    frame = ttk.Frame(dialog, padding=(20, 0))
    frame.pack()
    ttk.Radiobutton(
        frame, text="桌面程序（EXE / GUI）", variable=var_mode, value="desktop"
    ).pack(anchor="w", pady=4)
    ttk.Radiobutton(
        frame, text="网页版（浏览器访问，功能相同）", variable=var_mode, value="web"
    ).pack(anchor="w", pady=4)
    ttk.Checkbutton(
        frame, text="记住选择，下次不再询问", variable=var_remember
    ).pack(anchor="w", pady=(12, 0))

    def on_ok() -> None:
        result["mode"] = var_mode.get()
        result["remember"] = var_remember.get()
        dialog.destroy()
        root.destroy()

    ttk.Button(dialog, text="确定", command=on_ok, width=14).pack(pady=16)
    dialog.protocol("WM_DELETE_WINDOW", on_ok)

    root.wait_window(dialog)
    chosen = result["mode"] if result["mode"] in ("desktop", "web") else "desktop"
    if result["remember"]:
        cfg.ui_mode = chosen
        cfg.save()
    return chosen
