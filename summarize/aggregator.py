"""读取下载目录并汇总为三表 Excel（全量 + 可选按时间段分段主表）。"""
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, List, Optional, Tuple

LogFn = Callable[[str], None]
StatusFn = Callable[[str], None]

import pandas as pd

from config.settings import DOWNLOAD_DIR, SUMMARIZE_OUTPUT_DIR
from config.summarize_settings import SummarizeConfig
from summarize.app_bridge import (
    TARGET_COLUMNS,
    calculate_tax_info,
    create_final_table,
    create_settlement_summary,
    read_excel_file,
)
from summarize.date_filter import (
    DateRange,
    filter_by_date_range,
    filter_by_date_ranges,
    format_range_label,
    period_detail_sheet_name,
)



def list_downloaded_xlsx(
    download_dir: Path, *, output_prefix: str = "录音师薪资结算结果"
) -> List[Path]:
    if not download_dir.is_dir():
        return []
    return sorted(
        f
        for f in download_dir.glob("*.xlsx")
        if not f.stem.startswith(output_prefix)
    )


def _build_summary_tables(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    summary_df = create_settlement_summary(df)
    if summary_df.empty:
        return summary_df, pd.DataFrame()

    summary_df = summary_df.copy()
    summary_df["税后"] = summary_df["小计(元)"]

    tax_info_list = [
        calculate_tax_info(row["小计(元)"]) for _, row in summary_df.iterrows()
    ]
    summary_df["个税"] = [t for t, _ in tax_info_list]
    summary_df["税前"] = [b for _, b in tax_info_list]

    column_order = [
        "录音师",
        "整套",
        "新增",
        "全新单价",
        "补录单价",
        "小计(元)",
        "税后",
        "个税",
        "税前",
    ]
    summary_df = summary_df[column_order]
    final_df = create_final_table(summary_df)
    return summary_df, final_df


class WorkOrderAggregator:
    def __init__(self, config: Optional[SummarizeConfig] = None):
        self.config = config or SummarizeConfig.load()

    def _load_all_data(
        self,
        download_dir: Path,
        *,
        on_progress: Optional[StatusFn] = None,
    ) -> Tuple[pd.DataFrame, List[Tuple[str, str]]]:
        sheet_name = self.config.sheet_name
        files = list_downloaded_xlsx(
            download_dir, output_prefix=self.config.output_filename_prefix
        )
        if not files:
            raise RuntimeError(f"目录中没有工单 xlsx 文件: {download_dir}")

        processed: List[pd.DataFrame] = []
        errors: List[Tuple[str, str]] = []

        print(f"\n读取目录: {download_dir}（共 {len(files)} 个工单文件）")
        print("筛选依据: 主表「日期」列（对应原始提交时间，闭区间）")
        if sheet_name:
            print(f"工单内工作表: {sheet_name}")
        else:
            print("工单内工作表: 默认（每个文件的第一个工作表）")

        total = len(files)
        for idx, file_path in enumerate(files, start=1):
            if on_progress:
                on_progress(f"读取工单 {idx}/{total}: {file_path.name}")
            try:
                with open(file_path, "rb") as f:
                    content = BytesIO(f.read())
                df = read_excel_file(content, TARGET_COLUMNS, sheet_name)
                if df is not None and not df.empty:
                    processed.append(df)
                    line = f"  [OK] {file_path.name} ({len(df)} 行)"
                    print(line)
                    if on_progress:
                        on_progress(f"[OK] {file_path.name} · {len(df)} 行")
                else:
                    errors.append((file_path.name, "无数据"))
                    print(f"  [!] {file_path.name}: 无数据")
            except Exception as exc:
                errors.append((file_path.name, str(exc)))
                print(f"  [X] {file_path.name}: {exc}")

        if not processed:
            detail = "\n".join(f"  - {n}: {e}" for n, e in errors)
            raise RuntimeError(f"没有成功读取任何工单文件\n{detail}")

        all_data = pd.concat(processed, ignore_index=True)
        all_data = all_data[TARGET_COLUMNS]
        all_data = all_data.dropna(how="all")
        print(f"\n读取合计 {len(all_data)} 行")
        return all_data, errors

    def _write_full_summary_sheets(
        self, writer: pd.ExcelWriter, all_data: pd.DataFrame, *, label: str = "全量"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """写入主表、结算汇总、终表。"""
        summary_df, final_df = _build_summary_tables(all_data)
        all_data.to_excel(writer, sheet_name="主表", index=False)
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="结算汇总", index=False)
        if not final_df.empty:
            final_df.to_excel(writer, sheet_name="终表", index=False)
        print(
            f"\n[{label}] 主表 {len(all_data)} 行 | 结算汇总 {len(summary_df)} 人 | 终表 {len(final_df)} 人"
        )
        return summary_df, final_df

    def _write_period_detail_sheets(
        self,
        writer: pd.ExcelWriter,
        all_data: pd.DataFrame,
        ranges: List[DateRange],
    ) -> None:
        """按时间段仅写入分段主表（工单明细）。"""
        print(f"\n按 {len(ranges)} 个时间段写入分段主表 …")
        for start, end in ranges:
            period_df = filter_by_date_range(all_data, start, end)
            sheet_name = period_detail_sheet_name(start, end)
            label = format_range_label(start, end)
            period_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"  [{sheet_name}] {label} -> {len(period_df)} 行")

    def aggregate(
        self,
        download_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        *,
        skip_prompt: bool = False,
        date_ranges: Optional[List[DateRange]] = None,
        skip_date_prompt: bool = False,
        status_fn: Optional[StatusFn] = None,
        log_fn: Optional[LogFn] = None,
    ) -> Path:
        download_dir = Path(download_dir or DOWNLOAD_DIR)
        save_dir = Path(output_dir or SUMMARIZE_OUTPUT_DIR)
        save_dir.mkdir(parents=True, exist_ok=True)

        def _status(msg: str) -> None:
            print(msg, flush=True)
            if log_fn:
                log_fn(msg)
            if status_fn:
                status_fn(msg)

        if not skip_prompt and self.config.prompt_before_summarize:
            # 网页版/CLI 不走此处（skip_prompt=True），控制台交互在 pipeline.prepare_summarize 中处理
            print("汇总前确认已在 prepare_summarize 中处理")

        _status(f"读取工单目录: {download_dir}")
        all_data, errors = self._load_all_data(download_dir, on_progress=_status)
        _status(f"已合并 {len(all_data)} 行明细，开始生成 Excel …")

        ranges = date_ranges
        if ranges is None and self.config.prompt_for_date_ranges and not skip_date_prompt:
            # 时间段选择不在 aggregator 中进行，由 prepare_summarize 传入
            print("[!] 时间段选择应在外部完成")
            ranges = []
        if ranges is None:
            ranges = []

        summary_data = all_data
        if ranges:
            summary_data = filter_by_date_ranges(all_data, ranges)
            labels = "、".join(format_range_label(s, e) for s, e in sorted(ranges, key=lambda r: r[0]))
            _status(
                f"主表按 {len(ranges)} 个时间段筛选（闭区间）: {len(summary_data)} 行"
            )
            print(f"  时间段: {labels}")
            if summary_data.empty:
                raise RuntimeError("所选时间段内没有工单数据，请检查日历选择或工单「日期」列")

        _status("正在生成主表 / 结算汇总 / 终表 …")
        prefix = self.config.output_filename_prefix
        ts = datetime.now().strftime("%y_%m_%d_%H%M%S")
        output_path = save_dir / f"{prefix}_{ts}.xlsx"
        tmp_path = save_dir / f".~{prefix}_{ts}.xlsx.tmp"

        sheet_label = "筛选" if ranges else "全量"

        try:
            with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
                self._write_full_summary_sheets(
                    writer, summary_data, label=sheet_label
                )
                if ranges:
                    _status(f"正在写入 {len(ranges)} 个时间段分段主表 …")
                    self._write_period_detail_sheets(writer, all_data, ranges)
            # 先写临时文件再替换，确保汇总结束瞬间桌面可见完整 xlsx
            if output_path.exists():
                output_path.unlink()
            os.replace(tmp_path, output_path)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        # 刷新目录时间戳，便于资源管理器立即显示新文件
        try:
            os.utime(save_dir, None)
        except OSError:
            pass

        done_msg = f"汇总完成，已保存: {output_path}"
        _status(done_msg)
        print(f"\n汇总完成（已保存到桌面）: {output_path}")
        if errors:
            msg = f"（{len(errors)} 个工单读取异常已跳过）"
            print(f"  {msg}")
            _status(msg)
        return output_path
