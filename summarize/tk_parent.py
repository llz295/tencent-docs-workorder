"""与 CustomTkinter 主窗口共用的 Tk 弹窗辅助（禁止再创建第二个 Tk 根）。"""
from __future__ import annotations

import tkinter as tk
from typing import Optional


def modal_toplevel(parent: tk.Misc) -> tk.Toplevel:
    """创建模态子窗口，依附已有主窗口。"""
    top = tk.Toplevel(parent)
    top.transient(parent.winfo_toplevel())
    top.attributes("-topmost", True)
    top.grab_set()
    return top


def show_modal(top: tk.Toplevel) -> None:
    top.update_idletasks()
    top.deiconify()
    top.lift()
    top.focus_force()
    top.wait_window()
