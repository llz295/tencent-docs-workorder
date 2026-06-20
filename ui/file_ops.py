"""配置文件路径展示、打开、文件夹定位。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk


def open_path_in_explorer(path: Path) -> None:
    path = path.resolve()
    if path.is_file():
        path = path.parent
    if not path.exists():
        messagebox.showwarning("路径不存在", str(path))
        return
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def open_file_with_default_app(path: Path) -> None:
    path = path.resolve()
    if not path.is_file():
        messagebox.showwarning("文件不存在", f"请先保存或创建:\n{path}")
        return
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def read_text_file(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
