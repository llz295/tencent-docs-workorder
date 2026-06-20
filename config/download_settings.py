"""下载并发配置（文件 / 环境变量 / 命令行）。"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR, DEFAULT_DOWNLOAD_CONCURRENCY

DOWNLOAD_CONFIG_PATH = DATA_DIR / "download_config.json"
ENV_CONCURRENCY = "TENCENT_DOCS_CONCURRENCY"


@dataclass(frozen=True)
class DownloadConfig:
    """并发下载配置。"""

    concurrency: int = DEFAULT_DOWNLOAD_CONCURRENCY

    def __post_init__(self) -> None:
        if self.concurrency < 1:
            raise ValueError("concurrency 至少为 1")

    @classmethod
    def load(
        cls,
        config_path: Optional[Path] = None,
        cli_concurrency: Optional[int] = None,
    ) -> "DownloadConfig":
        """
        优先级：命令行 > 环境变量 > download_config.json > 代码默认值
        """
        concurrency = DEFAULT_DOWNLOAD_CONCURRENCY

        path = config_path or DOWNLOAD_CONFIG_PATH
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if "concurrency" in data:
                concurrency = int(data["concurrency"])

        env_val = os.environ.get(ENV_CONCURRENCY)
        if env_val is not None:
            concurrency = int(env_val)

        if cli_concurrency is not None:
            concurrency = cli_concurrency

        return cls(concurrency=concurrency)

    def save(self, path: Optional[Path] = None) -> None:
        target = path or DOWNLOAD_CONFIG_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump({"concurrency": self.concurrency}, f, ensure_ascii=False, indent=2)
