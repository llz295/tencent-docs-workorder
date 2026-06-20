"""登录态管理（异步）。"""
import json
from pathlib import Path
from typing import Tuple

from playwright.async_api import Browser, BrowserContext, Playwright

from auth.cookie_utils import auth_cookies_expired, has_auth_cookies
from auth.session_probe import verify_session_by_probe_download
from config.settings import PROBE_WAIT_SEC, STORAGE_STATE_PATH
from core.browser_factory import BrowserFactory
from pages.login_page import LoginPage


def _log_login_required() -> None:
    print("\n" + "=" * 50)
    print("腾讯文档登录已失效或未登录。")
    print("正在打开有头浏览器，请使用微信扫码登录…")
    print("=" * 50 + "\n")


class SessionManager:
    def __init__(self, playwright: Playwright):
        self._pw = playwright
        self._factory = BrowserFactory(playwright)

    async def ensure_session(
        self, headless: bool = True
    ) -> Tuple[BrowserContext, BrowserFactory]:
        fresh_login = False

        if self._needs_interactive_login():
            await self._interactive_login()
            fresh_login = True

        await self._factory.launch(headless=headless)
        context = await self._factory.new_context(headless=headless)

        if not fresh_login:
            if not await verify_session_by_probe_download(context):
                print(
                    f"ℹ 探针表格下载失败（{PROBE_WAIT_SEC}s 内未成功），会话已失效"
                )
                await context.close()
                await self._factory.close()
                self._invalidate_session()
                await self._interactive_login()
                fresh_login = True
                await self._factory.launch(headless=headless)
                context = await self._factory.new_context(headless=headless)

        if fresh_login:
            mode = "无头" if headless else "有头"
            print(f"✅ 扫码登录完成，{mode}模式继续（已跳过探针复验）")
        else:
            mode = "无头" if headless else "有头"
            print(f"✅ 会话有效（探针下载成功），{mode}模式继续")

        return context, self._factory

    def _storage_path(self) -> Path:
        return Path(STORAGE_STATE_PATH)

    def _load_storage_cookies(self) -> list:
        path = self._storage_path()
        if not path.is_file():
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("cookies", [])

    def _needs_interactive_login(self) -> bool:
        if not self._storage_path().is_file():
            print("ℹ 未发现本地会话，需要首次登录")
            return True

        cookies = self._load_storage_cookies()
        if not has_auth_cookies(cookies):
            print("ℹ 会话文件缺少登录 Cookie")
            return True

        if auth_cookies_expired(cookies):
            print("ℹ 会话 Cookie 已过期")
            return True

        return False

    async def _launch_login_browser(self) -> Browser:
        """扫码专用：独立 Chromium，不用系统 Chrome 配置，避免误用已有登录态。"""
        kwargs = {"headless": False}
        return await self._pw.chromium.launch(**kwargs)

    def _invalidate_session(self) -> None:
        stale = self._storage_path()
        if not stale.is_file():
            return
        backup = stale.with_suffix(".json.bak")
        try:
            if backup.is_file():
                backup.unlink()
            stale.rename(backup)
            print(f"ℹ 已备份失效会话: {backup.name}")
        except OSError as exc:
            print(f"ℹ 备份旧会话失败: {exc}")
            try:
                stale.unlink()
            except OSError:
                pass

    async def _interactive_login(self) -> None:
        _log_login_required()
        print("🌐 打开有头浏览器，等待微信扫码登录…")
        print("   （干净环境，不加载旧 session.json）")

        self._invalidate_session()

        login_browser: Browser | None = None
        context: BrowserContext | None = None
        try:
            login_browser = await self._launch_login_browser()
            context = await login_browser.new_context(accept_downloads=True)
            page = await context.new_page()
            login = LoginPage(page)
            await login.open_home()
            try:
                await page.bring_to_front()
            except Exception:
                pass

            try:
                logged_in = await login.wait_until_logged_in()
            except Exception as exc:
                print(f"❌ 登录过程异常: {exc}")
                raise RuntimeError(f"登录过程异常: {exc}") from exc

            if not logged_in:
                raise RuntimeError("登录失败或超时，请重新点击下载并完成扫码")

            self._storage_path().parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(self._storage_path()))
            print(f"💾 会话已保存: {self._storage_path()}")
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if login_browser:
                try:
                    await login_browser.close()
                except Exception:
                    pass
            print("🔒 扫码浏览器已关闭，后续使用无头模式")

    async def save_storage_from_context(self, context: BrowserContext) -> None:
        self._storage_path().parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(self._storage_path()))
