"""通过探针表格实际下载验证登录态是否有效。"""
import shutil
import tempfile
from pathlib import Path

from config.settings import PROBE_SHEET_URL, PROBE_WAIT_SEC, apply_app_config
from playwright.async_api import BrowserContext


async def verify_session_by_probe_download(
    context: BrowserContext,
    *,
    probe_url: str | None = None,
    timeout_sec: int | None = None,
) -> bool:
    """尝试下载探针表格；下载失败即视为 cookies 失效（快速、无重试）。"""
    from pages.sheet_page import SheetPage

    apply_app_config()
    url = (probe_url or PROBE_SHEET_URL).strip()
    wait = timeout_sec if timeout_sec is not None else PROBE_WAIT_SEC
    if not url:
        print("  … 探针 URL 未配置")
        return False

    tmp = Path(tempfile.mkdtemp(prefix="tencent_probe_"))
    page = await context.new_page()
    try:
        sheet = SheetPage(page)
        ok = await sheet.probe_download(
            url, str(tmp), timeout_sec=wait, label="登录探针"
        )
        if not ok:
            print("  … 探针表格下载失败（视为登录失效）")
        return ok
    except Exception as exc:
        print(f"  … 探针下载异常: {exc}")
        return False
    finally:
        try:
            await page.close()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
