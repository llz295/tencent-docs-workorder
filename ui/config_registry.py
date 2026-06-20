"""所有可编辑配置文件登记。"""
from dataclasses import dataclass
from pathlib import Path
from typing import List

from config.app_config import AppConfig
from config.download_settings import DOWNLOAD_CONFIG_PATH
from config.settings import DATA_DIR, DOC_URLS_PATH, STORAGE_STATE_PATH
from config.summarize_settings import SUMMARIZE_CONFIG_PATH
from config.voice_actor_pricing import config_path as voice_actor_config_path


@dataclass(frozen=True)
class ConfigFileEntry:
    key: str
    title: str
    path: Path
    description: str
    editable_in_ui: bool = True


def all_config_files() -> List[ConfigFileEntry]:
    app_path = AppConfig.load().path
    return [
        ConfigFileEntry(
            "app_config",
            "应用配置 app_config.json",
            app_path,
            "路径、超时、浏览器、登录探测 URL",
        ),
        ConfigFileEntry(
            "download_config",
            "下载配置 download_config.json",
            DOWNLOAD_CONFIG_PATH,
            "并发下载数量",
        ),
        ConfigFileEntry(
            "summarize_config",
            "汇总配置 summarize_config.json",
            SUMMARIZE_CONFIG_PATH,
            "汇总弹窗、工作表、输出文件名",
        ),
        ConfigFileEntry(
            "voice_actor_config",
            "价格表 voice_actor_config.json",
            voice_actor_config_path(),
            "录音师化名映射 + 全新(套)/补录(条)单价",
        ),
        ConfigFileEntry(
            "doc_urls",
            "文档列表 doc_urls.json",
            DOC_URLS_PATH,
            "录音师腾讯文档 URL 列表",
        ),
        ConfigFileEntry(
            "session",
            "登录会话 session.json",
            STORAGE_STATE_PATH,
            "Playwright 登录态（自动生成，一般勿手改）",
            editable_in_ui=False,
        ),
    ]


def data_directory() -> Path:
    return DATA_DIR
