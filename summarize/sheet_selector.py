"""汇总前选择 / 输入 Excel 工作表名称。"""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Callable, List, Optional

import tkinter as tk
from tkinter import ttk

from summarize.tk_parent import modal_toplevel, show_modal

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _sheet_names_from_zip(file_path: Path) -> List[str]:
    """直接从 xlsx 压缩包读 workbook.xml，绕过 openpyxl 样式解析。"""
    with zipfile.ZipFile(file_path, "r") as zf:
        with zf.open("xl/workbook.xml") as f:
            root = ET.parse(f).getroot()
    names = []
    for el in root.findall("main:sheets/main:sheet", _NS):
        name = el.get("name")
        if name:
            names.append(name)
    return names


def _sheet_names_via_fix_excel(file_path: Path) -> List[str]:
    """腾讯文档导出的 xlsx 样式异常时，先修复再读。"""
    import pandas as pd

    from summarize.app_bridge import fix_excel_file_style

    with open(file_path, "rb") as f:
        fixed = fix_excel_file_style(BytesIO(f.read()))
    with pd.ExcelFile(fixed, engine="openpyxl") as xl:
        return list(xl.sheet_names)


def list_sheet_names(file_path: Path) -> List[str]:
    """读取 xlsx 中全部工作表名（多种策略）。"""
    strategies: List[Callable[[Path], List[str]]] = [
        _sheet_names_from_zip,
        _sheet_names_via_fix_excel,
    ]
    errors: List[str] = []
    for fn in strategies:
        try:
            names = fn(file_path)
            if names:
                return names
        except Exception as exc:
            errors.append(f"{fn.__name__}: {exc}")
    if errors:
        print("[!] 自动读取工作表列表失败，请手动输入表名")
        for e in errors:
            print(f"    {e}")
    return []


def _list_work_order_xlsx(
    download_dir: Path,
    *,
    output_prefix: str = "录音师薪资结算结果",
) -> List[Path]:
    if not download_dir.is_dir():
        return []
    return sorted(
        f
        for f in download_dir.glob("*.xlsx")
        if not f.stem.startswith(output_prefix)
    )


def _index_sort_key(path: Path) -> int:
    """按文件名前缀序号排序，如 1_贝儿.xlsx → 1。"""
    head = path.stem.split("_", 1)[0]
    try:
        return int(head)
    except ValueError:
        return 999_999


def find_sample_xlsx(
    download_dir: Path,
    *,
    prefer_name_contains: str = "贝儿",
    output_prefix: str = "录音师薪资结算结果",
) -> Optional[Path]:
    """
    选取用于展示 sheet 列表的样例工单。

    优先级：文件名包含 prefer_name_contains（默认「贝儿」）>
    按下载序号 1、2、3… 最小的文件。
    """
    files = _list_work_order_xlsx(download_dir, output_prefix=output_prefix)
    if not files:
        return None

    keyword = (prefer_name_contains or "").strip()
    if keyword:
        for f in files:
            if keyword in f.name:
                return f

    return min(files, key=_index_sort_key)


class SheetPickerDialog:
    """在 GUI 主窗口上弹出工作表列表（不创建第二个 Tk 根）。"""

    def __init__(
        self,
        parent: tk.Misc,
        sample_file: Path,
        names: List[str],
    ) -> None:
        self._result: Optional[str] = None
        self.win = modal_toplevel(parent)
        self.win.title("选择汇总工作表")
        self.win.geometry("420x480")

        ttk.Label(
            self.win,
            text=f"样例文件: {sample_file.name}",
            wraplength=380,
        ).pack(anchor=tk.W, padx=12, pady=(12, 6))
        ttk.Label(self.win, text="双击或选中后点「确定」:").pack(anchor=tk.W, padx=12)

        frame = ttk.Frame(self.win, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox = tk.Listbox(
            frame, height=16, yscrollcommand=scroll.set, font=("Microsoft YaHei UI", 10)
        )
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self._listbox.yview)
        for name in names:
            self._listbox.insert(tk.END, name)
        self._listbox.selection_set(0)
        self._listbox.bind("<Double-Button-1>", lambda _e: self._on_ok())

        bar = ttk.Frame(self.win, padding=8)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="取消", command=self._on_cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(bar, text="确定", command=self._on_ok).pack(side=tk.RIGHT)

    def _on_ok(self) -> None:
        sel = self._listbox.curselection()
        if sel:
            self._result = self._listbox.get(sel[0])
        elif self._listbox.size() > 0:
            self._result = self._listbox.get(0)
        self.win.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.win.destroy()

    def show(self) -> Optional[str]:
        show_modal(self.win)
        return self._result


def prompt_sheet_name_interactive(
    sample_file: Optional[Path],
    *,
    parent: Optional[tk.Misc] = None,
) -> Optional[str]:
    """
    交互式选择工作表：
    - 输入序号 1-N
    - 或直接输入完整 sheet 名
    - 回车 / 0：使用第一个工作表
    """
    names: List[str] = []
    if sample_file and sample_file.is_file():
        names = list_sheet_names(sample_file)
        print("\n" + "=" * 40)
        print(f"样例文件: {sample_file.name}")
    else:
        print("\n" + "=" * 40)
        print("[!] 下载目录中未找到 xlsx，请直接输入工作表名称")

    if parent is not None and names and sample_file:
        picked = SheetPickerDialog(parent, sample_file, names).show()
        if picked:
            print(f"-> 已选择: {picked}")
            return picked
        print("已取消选择工作表")
        return None

    if names:
        print("可选工作表 (sheet):")
        for i, name in enumerate(names, 1):
            print(f"  {i}. {name}")
        print("  0 / 回车 = 使用第 1 个工作表")
        print("  也可直接输入工作表完整名称（区分大小写）")
    else:
        print("请直接输入要汇总的工作表名称（区分大小写）")
    print("=" * 40)

    try:
        from tkinter import simpledialog

        if parent is not None:
            raw = simpledialog.askstring(
                "选择汇总工作表",
                "请输入工作表名称",
                parent=parent,
            )
        else:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            if names:
                hint = "序号(1-%d)、0=默认、或完整表名" % len(names)
            else:
                hint = "请输入工作表名称"
            raw = simpledialog.askstring("选择汇总工作表", hint, parent=root)
            root.destroy()
        if raw is None:
            print("已取消选择工作表")
            return None
        choice = raw.strip()
    except Exception:
        choice = input("\n请输入序号或工作表名称: ").strip()

    if not names:
        if not choice:
            print("[!] 未输入工作表名称")
            return None
        print(f"-> 使用工作表: {choice}")
        return choice

    return _parse_sheet_choice(choice, names)


def _parse_sheet_choice(choice: str, names: List[str]) -> Optional[str]:
    if not choice or choice == "0":
        selected = names[0]
        print(f"-> 使用默认工作表: {selected}")
        return selected

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(names):
            selected = names[idx - 1]
            print(f"-> 已选择: {selected}")
            return selected
        print(f"[!] 序号无效，有效范围 1-{len(names)}")
        return None

    if choice in names:
        print(f"-> 已选择: {choice}")
        return choice

    print(f"-> 使用自定义工作表名: {choice}")
    return choice


def resolve_sheet_name(
    sample_file: Optional[Path],
    *,
    config_sheet: Optional[str] = None,
    cli_sheet: Optional[str] = None,
    prompt_interactive: bool = True,
    parent: Optional[tk.Misc] = None,
) -> Optional[str]:
    """
    确定汇总使用的 sheet 名。

    优先级：命令行 --sheet > 配置文件 sheet_name > 交互输入 > None(首个工作表)
    """
    if cli_sheet is not None and cli_sheet.strip():
        name = cli_sheet.strip()
        print(f"工作表(命令行): {name}")
        return name

    if config_sheet and config_sheet.strip():
        name = config_sheet.strip()
        print(f"工作表(配置文件): {name}")
        return name

    if prompt_interactive:
        return prompt_sheet_name_interactive(sample_file, parent=parent)

    print("工作表: 默认（Excel 第一个工作表）")
    return None
