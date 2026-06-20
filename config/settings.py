"""全局配置（路径、超时、浏览器参数）。"""
from pathlib import Path

from config.app_config import AppConfig
from config.runtime_paths import ensure_data_files, get_base_dir

ensure_data_files()

BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
STORAGE_STATE_PATH = DATA_DIR / "session.json"
DOC_URLS_PATH = DATA_DIR / "doc_urls.json"

DOCS_HOME = "https://docs.qq.com"

# 下载
DEFAULT_DOWNLOAD_CONCURRENCY = 5
SHEET_LOAD_WAIT_MS = 2000
EDITOR_READY_TIMEOUT_MS = 25_000
MENU_READY_TIMEOUT_MS = 8_000
MENU_EXPAND_WAIT_SEC = 1
SHEET_OPEN_MAX_RETRIES = 1
RETRY_ROUND_DELAY_SEC = 3

# 登录态检测
AUTH_COOKIE_NAMES = ("uid", "access_token", "SID", "DOC_SID")
LOGIN_WAIT_TIMEOUT_SEC = 300
LOGIN_POLL_INTERVAL_SEC = 2
PROBE_WAIT_SEC = 20

# 浏览器
HEADLESS = True
BROWSER_CHANNEL = None

# 动态路径（由 app_config 覆盖）
PROBE_SHEET_URL = "https://docs.qq.com/sheet/DTHN5UWdjZmxmWG9P"
DOWNLOAD_DIR = Path.home() / "Desktop" / "录音师工单"
SUMMARIZE_OUTPUT_DIR = Path.home() / "Desktop"


def apply_app_config(cfg: AppConfig | None = None) -> AppConfig:
    """将 app_config.json 应用到本模块全局变量。"""
    global PROBE_SHEET_URL, DOWNLOAD_DIR, SUMMARIZE_OUTPUT_DIR
    global RETRY_ROUND_DELAY_SEC, SHEET_LOAD_WAIT_MS, EDITOR_READY_TIMEOUT_MS
    global MENU_READY_TIMEOUT_MS, SHEET_OPEN_MAX_RETRIES
    global LOGIN_WAIT_TIMEOUT_SEC, LOGIN_POLL_INTERVAL_SEC, HEADLESS, BROWSER_CHANNEL
    global PROBE_WAIT_SEC

    ac = cfg or AppConfig.load()
    PROBE_SHEET_URL = ac.probe_sheet_url
    dd = ac.download_dir.strip() or str(Path.home() / "Desktop" / "录音师工单")
    od = ac.summarize_output_dir.strip() or str(Path.home() / "Desktop")
    DOWNLOAD_DIR = Path(dd)
    SUMMARIZE_OUTPUT_DIR = Path(od)
    RETRY_ROUND_DELAY_SEC = ac.retry_round_delay_sec
    SHEET_LOAD_WAIT_MS = ac.sheet_load_wait_ms
    EDITOR_READY_TIMEOUT_MS = ac.editor_ready_timeout_ms
    MENU_READY_TIMEOUT_MS = ac.menu_ready_timeout_ms
    SHEET_OPEN_MAX_RETRIES = ac.sheet_open_max_retries
    LOGIN_WAIT_TIMEOUT_SEC = ac.login_wait_timeout_sec
    LOGIN_POLL_INTERVAL_SEC = ac.login_poll_interval_sec
    PROBE_WAIT_SEC = max(5, min(120, int(getattr(ac, "probe_wait_sec", 20) or 20)))
    HEADLESS = ac.headless
    BROWSER_CHANNEL = ac.browser_channel
    return ac


apply_app_config()
