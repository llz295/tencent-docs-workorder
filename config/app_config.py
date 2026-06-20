"""应用级配置（路径、超时、浏览器）— 由 GUI 读写 data/app_config.json。"""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from config.runtime_paths import ensure_data_files, get_base_dir


def _default_download_dir() -> str:
    return str(Path.home() / "Desktop" / "录音师工单")


def _default_output_dir() -> str:
    return str(Path.home() / "Desktop")


@dataclass
class AppConfig:
    download_dir: str = field(default_factory=_default_download_dir)
    summarize_output_dir: str = field(default_factory=_default_output_dir)
    probe_sheet_url: str = "https://docs.qq.com/sheet/DTHN5UWdjZmxmWG9P"
    retry_round_delay_sec: int = 3
    login_wait_timeout_sec: int = 300
    login_poll_interval_sec: int = 2
    sheet_load_wait_ms: int = 2000
    editor_ready_timeout_ms: int = 25000
    menu_ready_timeout_ms: int = 8000
    sheet_open_max_retries: int = 1
    probe_wait_sec: int = 20
    headless: bool = True
    browser_channel: Optional[str] = None
    ui_mode: str = "ask"  # ask | desktop | web
    web_host: str = "0.0.0.0"
    web_port: int = 8765

    @property
    def path(self) -> Path:
        return ensure_data_files() / "app_config.json"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        cfg_path = path or ensure_data_files() / "app_config.json"
        if not cfg_path.is_file():
            inst = cls()
            inst.save(cfg_path)
            return inst
        with open(cfg_path, encoding="utf-8") as f:
            data = json.load(f)
        known = {k for k in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known}
        inst = cls(**filtered)
        if not str(inst.download_dir).strip():
            inst.download_dir = _default_download_dir()
        if not str(inst.summarize_output_dir).strip():
            inst.summarize_output_dir = _default_output_dir()
        return inst

    def save(self, path: Optional[Path] = None) -> None:
        cfg_path = path or self.path
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    def download_path(self) -> Path:
        return Path(self.download_dir).expanduser()

    def output_path(self) -> Path:
        return Path(self.summarize_output_dir).expanduser()


def data_dir() -> Path:
    return get_base_dir() / "data"
