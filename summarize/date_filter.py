"""按「日期」列（来源：提交时间）筛选工单。"""
from datetime import date
from typing import List, Tuple

import pandas as pd

DateRange = Tuple[date, date]


def parse_row_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.date


def filter_by_date_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """闭区间 [start, end] 筛选。"""
    if df.empty or "日期" not in df.columns:
        return df.iloc[0:0].copy()

    if start > end:
        start, end = end, start
    dates = parse_row_dates(df["日期"])
    mask = dates.notna() & (dates >= start) & (dates <= end)
    return df.loc[mask].copy()


def filter_by_date_ranges(df: pd.DataFrame, ranges: List[DateRange]) -> pd.DataFrame:
    """按多个闭区间筛选，按时间段顺序合并为主表数据（区间重叠行去重）。"""
    if df.empty or not ranges:
        return df.copy()

    sorted_ranges = sorted(
        ((min(a, b), max(a, b)) for a, b in ranges),
        key=lambda r: (r[0], r[1]),
    )
    parts: List[pd.DataFrame] = []
    for start, end in sorted_ranges:
        chunk = filter_by_date_range(df, start, end)
        if not chunk.empty:
            parts.append(chunk)

    if not parts:
        return df.iloc[0:0].copy()

    # 保留原始行号去重：仅合并区间重叠时的同一行，不误删内容相同的不同工单
    combined = pd.concat(parts)
    combined = combined[~combined.index.duplicated(keep="first")]

    if "日期" in combined.columns:
        sort_dates = parse_row_dates(combined["日期"])
        combined = (
            combined.assign(_sort_date=sort_dates)
            .sort_values("_sort_date", kind="stable", na_position="last")
            .drop(columns="_sort_date")
        )
    return combined.reset_index(drop=True)


def period_detail_sheet_name(start: date, end: date) -> str:
    """分段主表 sheet 名（含年份，Excel 最长 31 字符）。"""
    if start.year == end.year and start.month == end.month:
        name = f"{start.year}年{start.month}月{start.day}日-{end.day}日的工单"
    else:
        name = (
            f"{start.year}年{start.month}月{start.day}日-"
            f"{end.year}年{end.month}月{end.day}日的工单"
        )
    return name[:31]


def format_range_label(start: date, end: date) -> str:
    return f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"
