"""复用 vendor/app.py 或上级 app.py 中的汇总逻辑。"""
import sys
from pathlib import Path

from config.frozen_bootstrap import is_frozen
from config.runtime_paths import get_base_dir, get_bundle_dir

_POM_DIR = Path(__file__).resolve().parents[1]
_VENDOR_DIR = _POM_DIR / "vendor"
_PARENT_APP = _POM_DIR.parent / "app.py"


def _resolve_automation_root() -> Path:
    if is_frozen():
        return get_bundle_dir() or get_base_dir()
    if (_VENDOR_DIR / "app.py").is_file():
        return _VENDOR_DIR
    if _PARENT_APP.is_file():
        return _PARENT_APP.parent
    return _POM_DIR.parent


_AUTOMATION_ROOT = _resolve_automation_root()

for _p in (_POM_DIR, _AUTOMATION_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app as _app_module  # noqa: E402

from config.voice_actor_pricing import install_into_app  # noqa: E402

install_into_app(_app_module)

from app import (  # noqa: E402
    calculate_tax_info,
    create_final_table,
    create_settlement_summary,
    fix_excel_file_style,
    read_excel_file,
)

TARGET_COLUMNS = [
    "日期",
    "编号",
    "需求人",
    "发起部门",
    "项目名称",
    "需求场景描述",
    "服务重要性等级",
    "机器人任务名称",
    "录音师",
    "录音条数",
    "录音规格",
    "期望完成时间",
    "录音价格",
    "是否已协调",
    "预计完成时间",
    "备注",
    "需求是否完结",
]

__all__ = [
    "TARGET_COLUMNS",
    "read_excel_file",
    "fix_excel_file_style",
    "create_settlement_summary",
    "create_final_table",
    "calculate_tax_info",
]
