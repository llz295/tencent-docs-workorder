"""腾讯文档登录页（异步）。"""
import asyncio
import time

from auth.cookie_utils import auth_cookies_expired, has_auth_cookies
from config.settings import (
    DOCS_HOME,
    LOGIN_POLL_INTERVAL_SEC,
    LOGIN_WAIT_TIMEOUT_SEC,
)
from pages.base_page import BasePage


class LoginPage(BasePage):
    LOGIN_BUTTON = "text=登录"

    async def open_home(self) -> None:
        await self.goto(DOCS_HOME)
        await self.page.wait_for_timeout(800)

    async def _auth_cookies_ready(self) -> bool:
        cookies = await self.page.context.cookies()
        if not has_auth_cookies(cookies):
            return False
        if auth_cookies_expired(cookies):
            return False
        return True

    async def _is_login_ui_visible(self) -> bool:
        """页面上仍显示「登录」入口，说明尚未完成扫码。"""
        return await self.is_visible(self.LOGIN_BUTTON, timeout_ms=800)

    async def wait_until_logged_in(self) -> bool:
        """
        有头扫码阶段：仅用 Cookie + 首页无「登录」按钮判定，不做探针下载。
        探针下载留给扫码浏览器关闭后的无头会话校验。
        """
        deadline = time.time() + LOGIN_WAIT_TIMEOUT_SEC
        poll = 0
        confirm_hits = 0

        print(
            "⏳ 等待扫码登录（最长 {} 分钟），请勿关闭浏览器窗口…".format(
                LOGIN_WAIT_TIMEOUT_SEC // 60
            )
        )
        print("   判定规则：有效 Cookie 且首页不再显示「登录」")

        while time.time() < deadline:
            poll += 1

            if "sheet" in self.page.url or "/doc/" in self.page.url:
                await self.open_home()

            if await self._is_login_ui_visible():
                confirm_hits = 0
                if poll == 1 or poll % 5 == 0:
                    print("  … 等待扫码（页面仍显示「登录」）")
                await asyncio.sleep(LOGIN_POLL_INTERVAL_SEC)
                continue

            if not await self._auth_cookies_ready():
                confirm_hits = 0
                if poll % 10 == 0:
                    print("  … 等待有效登录 Cookie…")
                await asyncio.sleep(LOGIN_POLL_INTERVAL_SEC)
                continue

            confirm_hits += 1
            if confirm_hits >= 2:
                print("✅ 扫码登录成功，即将关闭有头浏览器并切换无头模式")
                return True

            await asyncio.sleep(LOGIN_POLL_INTERVAL_SEC)

        print("❌ 登录超时，请重新运行程序")
        return False
