"""页面对象基类（异步）。"""
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    async def goto(
        self, url: str, wait_until: str = "domcontentloaded", timeout_ms: int = 60_000
    ) -> None:
        await self.page.goto(url, wait_until=wait_until, timeout=timeout_ms)

    async def goto_safe(
        self, url: str, wait_until: str = "commit", timeout_ms: int = 60_000
    ) -> bool:
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            return True
        except PlaywrightError as exc:
            msg = str(exc)
            if "ERR_ABORTED" in msg or "net::" in msg:
                return True
            raise

    async def is_visible(self, locator: str, timeout_ms: int = 3000) -> bool:
        try:
            return await self.page.locator(locator).first.is_visible(timeout=timeout_ms)
        except PlaywrightTimeoutError:
            return False
