"""交互式日历：选择多个汇总时间段（上月整月 + 本月整月均可选）。"""
import calendar
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import List, Optional, Tuple

from summarize.tk_parent import modal_toplevel, show_modal

DateRange = Tuple[date, date]


def _month_add(year: int, month: int, delta: int) -> Tuple[int, int]:
    m = month + delta
    y = year
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return y, m


class DateRangePickerDialog:
    """展示上月整月 + 本月整月；高亮星期五、上月25~月末（仅提示，均可点选）。"""

    def __init__(
        self,
        reference: Optional[date] = None,
        *,
        parent: Optional[tk.Misc] = None,
    ):
        self.today = reference or date.today()
        self.cur_y, self.cur_m = self.today.year, self.today.month
        self.prev_y, self.prev_m = _month_add(self.cur_y, self.cur_m, -1)
        self._prev_month_first = date(self.prev_y, self.prev_m, 1)
        _, last_d = calendar.monthrange(self.prev_y, self.prev_m)
        self._prev_month_last = date(self.prev_y, self.prev_m, last_d)

        self.ranges: List[DateRange] = []
        self._pick_start: Optional[date] = None
        self._pick_end: Optional[date] = None
        self._day_buttons: dict[date, tk.Button] = {}
        self._owns_root = parent is None

        if parent is not None:
            self.root = modal_toplevel(parent)
        else:
            self.root = tk.Tk()
            self.root.attributes("-topmost", True)
        self.root.title("选择汇总时间段")
        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(
            top,
            text=(
                f"今天: {self.today}  |  每段须点选「起始日」和「结束日」（闭区间，含首尾）  |  "
                "可添加多段"
            ),
            wraplength=720,
        ).pack(anchor=tk.W)

        legend = ttk.Frame(self.root, padding=(8, 0))
        legend.pack(fill=tk.X)
        for text, color in [
            ("■ 星期五", "#fff3cd"),
            ("■ 上月25日~月末(参考)", "#cfe2ff"),
            ("■ 今天", "#d1e7dd"),
            ("■ 已选区间", "#a3cfbb"),
        ]:
            tk.Label(legend, text=text, bg=color, padx=6).pack(side=tk.LEFT, padx=4)

        cal_frame = ttk.Frame(self.root, padding=8)
        cal_frame.pack()

        self._render_month_panel(cal_frame, self.prev_y, self.prev_m, title="上月（整月）")
        self._render_month_panel(cal_frame, self.cur_y, self.cur_m, title="本月（整月）")

        pick_bar = ttk.Frame(self.root, padding=8)
        pick_bar.pack(fill=tk.X)
        self._lbl_pick = ttk.Label(pick_bar, text="当前选择: （未选）")
        self._lbl_pick.pack(side=tk.LEFT)
        ttk.Button(pick_bar, text="添加时间段", command=self._add_range).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(pick_bar, text="清除当前选择", command=self._clear_pick).pack(
            side=tk.RIGHT
        )

        list_frame = ttk.LabelFrame(self.root, text="已添加的时间段（仅用于分段主表）", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self._listbox = tk.Listbox(list_frame, height=6)
        self._listbox.pack(fill=tk.BOTH, expand=True)
        ttk.Button(list_frame, text="删除选中", command=self._remove_selected).pack(
            anchor=tk.E, pady=4
        )

        btn_bar = ttk.Frame(self.root, padding=8)
        btn_bar.pack(fill=tk.X)
        ttk.Label(
            btn_bar,
            text="不添加时间段点确定 = 仅生成全量主表/结算汇总/终表",
            foreground="gray",
        ).pack(side=tk.LEFT)
        ttk.Button(btn_bar, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_bar, text="取消", command=self._on_cancel).pack(side=tk.RIGHT)

        self._result: Optional[List[DateRange]] = None

    def _render_month_panel(
        self,
        parent: ttk.Frame,
        year: int,
        month: int,
        *,
        title: str,
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        frame.pack(side=tk.LEFT, padx=8)

        headers = ["一", "二", "三", "四", "五", "六", "日"]
        for c, h in enumerate(headers):
            ttk.Label(frame, text=h, width=4, anchor=tk.CENTER).grid(row=0, column=c)

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(year, month)

        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ttk.Label(frame, text="", width=4).grid(row=r, column=c)
                    continue

                d = date(year, month, day)
                bg = "white"
                if d.weekday() == 4:
                    bg = "#fff3cd"
                if d.year == self.prev_y and d.month == self.prev_m and d.day >= 25:
                    bg = "#cfe2ff"
                if d == self.today:
                    bg = "#d1e7dd"

                btn = tk.Button(
                    frame,
                    text=str(day),
                    width=3,
                    bg=bg,
                    relief=tk.RAISED,
                    command=lambda dd=d: self._on_day_click(dd),
                )
                btn.grid(row=r, column=c, padx=1, pady=1)
                self._day_buttons[d] = btn

    def _on_day_click(self, d: date) -> None:
        if self._pick_start is None:
            self._pick_start = d
            self._pick_end = None
        elif self._pick_end is None:
            if d < self._pick_start:
                self._pick_end = self._pick_start
                self._pick_start = d
            else:
                self._pick_end = d
        else:
            self._pick_start = d
            self._pick_end = None
        self._refresh_pick_label()
        self._refresh_day_highlights()

    def _refresh_pick_label(self) -> None:
        if self._pick_start and self._pick_end:
            text = f"当前选择: {self._pick_start} ~ {self._pick_end}（闭区间）"
        elif self._pick_start:
            text = f"当前选择: 起始 {self._pick_start}（请再点结束日）"
        else:
            text = "当前选择: （未选）"
        self._lbl_pick.config(text=text)

    def _refresh_day_highlights(self) -> None:
        for d, btn in self._day_buttons.items():
            base = "white"
            if d.weekday() == 4:
                base = "#fff3cd"
            if d.year == self.prev_y and d.month == self.prev_m and d.day >= 25:
                base = "#cfe2ff"
            if d == self.today:
                base = "#d1e7dd"
            if self._pick_start and d == self._pick_start:
                base = "#198754"
            if self._pick_end and d == self._pick_end:
                base = "#198754"
            if (
                self._pick_start
                and self._pick_end
                and self._pick_start <= d <= self._pick_end
            ):
                base = "#a3cfbb"
            try:
                btn.config(bg=base)
            except tk.TclError:
                pass

    def _clear_pick(self) -> None:
        self._pick_start = None
        self._pick_end = None
        self._refresh_pick_label()
        self._refresh_day_highlights()

    @staticmethod
    def _range_label(start: date, end: date) -> str:
        if start.year == end.year and start.month == end.month:
            return f"{start.year}年{start.month}月{start.day}日-{end.day}日"
        return (
            f"{start.year}年{start.month}月{start.day}日-"
            f"{end.year}年{end.month}月{end.day}日"
        )

    def _add_range(self) -> None:
        if not self._pick_start or not self._pick_end:
            messagebox.showwarning("提示", "请先点击选择起始日和结束日（闭区间，含首尾）")
            return

        start, end = self._pick_start, self._pick_end
        if start > end:
            start, end = end, start
        self.ranges.append((start, end))
        self._listbox.insert(tk.END, self._range_label(start, end))
        self._clear_pick()

    def _remove_selected(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._listbox.delete(idx)
        del self.ranges[idx]

    def _on_ok(self) -> None:
        self._result = list(self.ranges)
        self.root.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.root.destroy()

    def show(self) -> Optional[List[DateRange]]:
        if self._owns_root:
            self.root.mainloop()
        else:
            show_modal(self.root)
        return self._result


def pick_date_ranges(
    reference: Optional[date] = None,
    *,
    parent: Optional[tk.Misc] = None,
) -> Optional[List[DateRange]]:
    try:
        dialog = DateRangePickerDialog(reference, parent=parent)
        return dialog.show()
    except Exception as exc:
        print(f"[!] 日历弹窗失败: {exc}")
        if parent is not None:
            messagebox.showerror(
                "日历不可用",
                f"{exc}\n\n请关闭后重试，或在配置中关闭「汇总时弹出日历」。",
                parent=parent,
            )
            return None
        return _pick_ranges_console()


def _pick_ranges_console() -> Optional[List[DateRange]]:
    print("请输入时间段，格式: 2026-05-15 2026-05-22 （空行结束）")
    ranges: List[DateRange] = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        parts = line.replace("~", " ").split()
        if len(parts) >= 2:
            start = date.fromisoformat(parts[0])
            end = date.fromisoformat(parts[1])
            ranges.append((start, end))
    return ranges
