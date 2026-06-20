"""录音师化名映射与价格表（data/voice_actor_config.json）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from config.runtime_paths import ensure_data_files, get_base_dir

CONFIG_FILENAME = "voice_actor_config.json"


def config_path() -> Path:
    return ensure_data_files() / CONFIG_FILENAME


def _frozen_data_path() -> Optional[Path]:
    if getattr(sys, "frozen", False):
        p = get_base_dir() / "data" / CONFIG_FILENAME
        if p.is_file():
            return p
    return None


def _dev_data_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / CONFIG_FILENAME


def resolve_config_path() -> Path:
    frozen = _frozen_data_path()
    if frozen is not None:
        return frozen
    runtime = config_path()
    if runtime.is_file():
        return runtime
    dev = _dev_data_path()
    if dev.is_file():
        return dev
    return runtime


def load_config(*, path: Optional[Path] = None) -> Dict[str, Any]:
    cfg_path = path or resolve_config_path()
    if not cfg_path.is_file():
        raise FileNotFoundError(f"未找到价格配置: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("name_mapping"), dict):
        raise ValueError("name_mapping 必须是对象")
    if not isinstance(data.get("prices"), dict):
        raise ValueError("prices 必须是对象")
    return data


def save_config(data: Dict[str, Any], *, path: Optional[Path] = None) -> Path:
    cfg_path = path or config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return cfg_path


def get_name_mapping() -> Dict[str, str]:
    return {str(k): str(v) for k, v in load_config()["name_mapping"].items()}


def get_prices() -> Dict[str, Dict[str, float]]:
    raw = load_config()["prices"]
    out: Dict[str, Dict[str, float]] = {}
    for name, item in raw.items():
        if not isinstance(item, dict):
            continue
        out[str(name)] = {
            "full_price": float(item.get("full_price", 0)),
            "supplement_price": float(item.get("supplement_price", 0)),
        }
    return out


def validate_config(data: Dict[str, Any]) -> None:
    if not isinstance(data.get("name_mapping"), dict):
        raise ValueError("name_mapping 必须是 JSON 对象")
    if not isinstance(data.get("prices"), dict):
        raise ValueError("prices 必须是 JSON 对象")
    for name, item in data["prices"].items():
        if not isinstance(item, dict):
            raise ValueError(f"prices.{name} 必须是对象")
        for key in ("full_price", "supplement_price"):
            if key not in item:
                raise ValueError(f"prices.{name} 缺少 {key}")
            float(item[key])


def install_into_app(app_module: Any) -> None:
    """将 app.py 中的价格/映射函数指向配置文件。"""

    def _mapping() -> Dict[str, str]:
        return get_name_mapping()

    def _prices() -> Dict[str, Dict[str, float]]:
        return get_prices()

    app_module.get_voice_actor_mapping = _mapping
    app_module.get_voice_actor_prices = _prices


def reload_app_pricing() -> None:
    import app as app_module

    install_into_app(app_module)
