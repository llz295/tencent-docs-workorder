"""汇总完成后的桌面通知。"""
from pathlib import Path


def notify_summarize_saved(output_path: Path) -> None:
    """汇总文件落盘后提示，并可打开所在文件夹。"""
    path = output_path.resolve()
    message = f"汇总结果已保存:\n{path}"
    try:
        import tkinter as tk
        from tkinter import messagebox

        from ui.file_ops import open_path_in_explorer

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if messagebox.askyesno("汇总完成", message + "\n\n是否打开所在文件夹？", default="yes"):
            open_path_in_explorer(path)
        root.destroy()
    except Exception:
        print("\n" + message)
