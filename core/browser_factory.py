"""浏览器与上下文工厂（异步）。"""
from pathlib import Path
from typing import Optional, Union

from playwright.async_api import Browser, BrowserContext, Playwright

from config.settings import BROWSER_CHANNEL, HEADLESS, STORAGE_STATE_PATH

# 未传 storage_state 时：自动加载 data/session.json（若存在）
_USE_DEFAULT_SESSION = object()


class BrowserFactory:
    def __init__(self, playwright: Playwright):
        self._pw = playwright
        self._browser: Optional[Browser] = None

    async def launch(self, headless: bool = HEADLESS) -> Browser:
        kwargs: dict = {"headless": headless}
        channel = (BROWSER_CHANNEL or "").strip().lower() or None
        if channel in ("chrome", "msedge", "chrome-beta", "msedge-beta"):
            kwargs["channel"] = BROWSER_CHANNEL
        elif channel == "chromium" or (headless and channel is None):
            # 仅安装 chromium --no-shell 时，无头须用 channel=chromium（完整 Chromium），
            # 否则会去找 chromium_headless_shell 导致 Executable doesn't exist。
            kwargs["channel"] = "chromium"
        elif channel:
            kwargs["channel"] = BROWSER_CHANNEL
        self._browser = await self._pw.chromium.launch(**kwargs)
        return self._browser

    async def new_context(
        self,
        headless: bool = HEADLESS,
        storage_state: Union[Path, None, object] = _USE_DEFAULT_SESSION,
    ) -> BrowserContext:
        if self._browser is None:
            await self.launch(headless=headless)

        options = {"accept_downloads": True}
        if storage_state is _USE_DEFAULT_SESSION:
            path = STORAGE_STATE_PATH
            if path and Path(path).is_file():
                options["storage_state"] = str(path)
        elif storage_state is not None:
            options["storage_state"] = str(storage_state)

        return await self._browser.new_context(**options)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
