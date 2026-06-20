"""汇总前确认弹窗。"""
from __future__ import annotations

from typing import Optional

import tkinter as tk


def confirm_summarize(
    *, enabled: bool = True, parent: Optional[tk.Misc] = None
) -> bool:
    """
    询问是否进行下一步「汇总工单」。
    enabled=False 时直接返回 True（不弹窗）。
    """
    if not enabled:
        return True

    message = (
        "是否现在开始汇总录音师工单？\n\n"
        "将读取「录音师工单」文件夹中的 Excel，\n"
        "生成：主表 / 结算汇总 / 终表"
    )
    try:
        from tkinter import messagebox

        if parent is not None:
            return bool(
                messagebox.askyesno(
                    "汇总录音师工单", message, default="yes", parent=parent
                )
            )
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        ok = messagebox.askyesno("汇总录音师工单", message, default="yes")
        root.destroy()
        return bool(ok)
    except Exception:
        print("\n" + "=" * 50)
        print(message)
        print("=" * 50)
        answer = input("是否汇总？(y/n，默认 y): ").strip().lower()
        return answer in ("", "y", "yes")
