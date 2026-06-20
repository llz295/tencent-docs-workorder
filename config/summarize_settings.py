"""汇总工单配置。"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR

SUMMARIZE_CONFIG_PATH = DATA_DIR / "summarize_config.json"
ENV_AUTO_SUMMARIZE = "TENCENT_DOCS_AUTO_SUMMARIZE"
ENV_PROMPT_SUMMARIZE = "TENCENT_DOCS_PROMPT_SUMMARIZE"


@dataclass(frozen=True)
class SummarizeConfig:
    prompt_before_summarize: bool = True
    auto_summarize_after_download: bool = False
    prompt_for_sheet_name: bool = True
    prompt_for_date_ranges: bool = True
    sheet_name: Optional[str] = None
    output_filename_prefix: str = "录音师薪资结算结果"
    sample_file_keyword: str = "贝儿"

    @classmethod
    def load(
        cls,
        *,
        cli_prompt: Optional[bool] = None,
        cli_auto: Optional[bool] = None,
        cli_sheet: Optional[str] = None,
        cli_prompt_sheet: Optional[bool] = None,
        cli_prompt_date: Optional[bool] = None,
    ) -> "SummarizeConfig":
        prompt = True
        auto = False
        prompt_sheet = True
        prompt_date = True
        sheet_name: Optional[str] = None
        prefix = "录音师薪资结算结果"
        sample_keyword = "贝儿"

        if SUMMARIZE_CONFIG_PATH.is_file():
            with open(SUMMARIZE_CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            prompt = bool(data.get("prompt_before_summarize", prompt))
            auto = bool(data.get("auto_summarize_after_download", auto))
            prompt_sheet = bool(data.get("prompt_for_sheet_name", prompt_sheet))
            prompt_date = bool(data.get("prompt_for_date_ranges", prompt_date))
            raw_sheet = data.get("sheet_name", "")
            sheet_name = raw_sheet.strip() or None
            prefix = data.get("output_filename_prefix", prefix)
            sample_keyword = data.get("sample_file_keyword", sample_keyword) or "贝儿"

        if os.environ.get(ENV_PROMPT_SUMMARIZE) is not None:
            prompt = os.environ.get(ENV_PROMPT_SUMMARIZE, "1").lower() in (
                "1",
                "true",
                "yes",
            )
        if os.environ.get(ENV_AUTO_SUMMARIZE) is not None:
            auto = os.environ.get(ENV_AUTO_SUMMARIZE, "0").lower() in (
                "1",
                "true",
                "yes",
            )

        if cli_prompt is not None:
            prompt = cli_prompt
        if cli_auto is not None:
            auto = cli_auto
        if cli_sheet is not None:
            sheet_name = cli_sheet.strip() or None
        if cli_prompt_sheet is not None:
            prompt_sheet = cli_prompt_sheet
        if cli_prompt_date is not None:
            prompt_date = cli_prompt_date

        return cls(
            prompt_before_summarize=prompt,
            auto_summarize_after_download=auto,
            prompt_for_sheet_name=prompt_sheet,
            prompt_for_date_ranges=prompt_date,
            sheet_name=sheet_name,
            output_filename_prefix=prefix,
            sample_file_keyword=sample_keyword,
        )

    def save(self, path: Optional[Path] = None) -> None:
        target = path or SUMMARIZE_CONFIG_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "prompt_before_summarize": self.prompt_before_summarize,
            "auto_summarize_after_download": self.auto_summarize_after_download,
            "prompt_for_sheet_name": self.prompt_for_sheet_name,
            "prompt_for_date_ranges": self.prompt_for_date_ranges,
            "sheet_name": self.sheet_name or "",
            "output_filename_prefix": self.output_filename_prefix,
            "sample_file_keyword": self.sample_file_keyword,
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
