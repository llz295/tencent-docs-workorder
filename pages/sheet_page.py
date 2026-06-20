"""腾讯文档表格页（异步下载）。"""
import asyncio
import os
import shutil
import time

from config.settings import (
    EDITOR_READY_TIMEOUT_MS,
    MENU_EXPAND_WAIT_SEC,
    MENU_READY_TIMEOUT_MS,
    SHEET_LOAD_WAIT_MS,
    SHEET_OPEN_MAX_RETRIES,
)
from pages.base_page import BasePage
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class SheetPage(BasePage):
    MORE_BUTTON = "//div[contains(@class, 'titlebar-icon-more')]"
    DOWNLOAD_MENU_ITEM = "//*[text()='下载']"
    LOGIN_BUTTON = "text=登录"

    async def _wait_locator_visible(self, locator: str, timeout_ms: int) -> bool:
        try:
            await self.page.locator(locator).first.wait_for(
                state="visible", timeout=timeout_ms
            )
            return True
        except PlaywrightTimeoutError:
            return False

    async def open_sheet(self, url: str) -> bool:
        """打开表格并等待「更多」按钮出现。"""
        await self.goto_safe(url)
        if await self._wait_locator_visible(self.MORE_BUTTON, EDITOR_READY_TIMEOUT_MS):
            return True
        # 部分文档加载较慢，再等一轮固定时间后重试检测
        await self.page.wait_for_timeout(SHEET_LOAD_WAIT_MS)
        return await self._wait_locator_visible(self.MORE_BUTTON, 10_000)

    async def is_editor_ready(self) -> bool:
        return await self._wait_locator_visible(self.MORE_BUTTON, 5000)

    async def probe_download(
        self,
        url: str,
        download_dir: str,
        *,
        timeout_sec: int = 20,
        label: str = "登录探针",
    ) -> bool:
        """探针专用：无页面重试；若出现登录页则立即失败，否则等待「更多」直至超时。"""
        deadline = time.monotonic() + timeout_sec

        def remaining_ms(min_ms: int = 300) -> int:
            left = int((deadline - time.monotonic()) * 1000)
            return max(min_ms, left)

        try:
            print(f"🔍 探针: {label}（超时 {timeout_sec}s，不重试）")
            nav_timeout = min(30_000, max(5000, remaining_ms(5000)))
            await self.page.goto(
                url, wait_until="domcontentloaded", timeout=nav_timeout
            )

            if await self.is_visible(self.LOGIN_BUTTON, timeout_ms=1500):
                print("  … 探针：页面显示「登录」（会话已失效）")
                return False

            wait_more_ms = remaining_ms()
            if not await self._wait_locator_visible(self.MORE_BUTTON, wait_more_ms):
                if await self.is_visible(self.LOGIN_BUTTON, timeout_ms=800):
                    print("  … 探针：页面显示「登录」（会话已失效）")
                else:
                    print(
                        f"  … 探针：{wait_more_ms // 1000}s 内未找到「更多」按钮"
                        "（表格可能仍在加载，可调大探针等待秒数）"
                    )
                return False

            more = self.page.locator(self.MORE_BUTTON).first
            await more.click()
            await asyncio.sleep(min(MENU_EXPAND_WAIT_SEC, 0.5))

            if not await self._wait_locator_visible(
                self.DOWNLOAD_MENU_ITEM, remaining_ms()
            ):
                print("  … 探针：未找到「下载」菜单")
                return False

            download_btn = self.page.locator(self.DOWNLOAD_MENU_ITEM).first
            async with self.page.expect_download(timeout=remaining_ms()) as download_info:
                await download_btn.click()

            download = await download_info.value
            temp_path = await download.path()
            os.makedirs(download_dir, exist_ok=True)
            filename = f"probe_{download.suggested_filename}"
            final_path = os.path.join(download_dir, filename)
            shutil.move(temp_path, final_path)
            size_kb = os.path.getsize(final_path) / 1024
            print(f"  ✅ 探针下载成功 ({size_kb:.1f} KB)")
            return True
        except PlaywrightTimeoutError:
            print(f"  … 探针超时（>{timeout_sec}s）")
            return False
        except Exception as exc:
            print(f"  … 探针失败: {exc}")
            return False

    async def download_sheet(
        self, url: str, download_dir: str, index: int, label: str = ""
    ) -> bool:
        tag = label or url
        try:
            print(f"🚀 [{index}] {tag}")

            ready = False
            for attempt in range(SHEET_OPEN_MAX_RETRIES + 1):
                if attempt > 0:
                    print(f"  [{index}] 页面未就绪，重试打开 ({attempt}/{SHEET_OPEN_MAX_RETRIES})…")
                ready = await self.open_sheet(url)
                if ready:
                    break

            if not ready:
                print(f"  ⚠ [{index}] 未找到「更多」按钮（页面加载超时）")
                return False

            more = self.page.locator(self.MORE_BUTTON).first
            await more.click()
            print(f"  [{index}] 已点击「更多」")
            await asyncio.sleep(MENU_EXPAND_WAIT_SEC)

            if not await self._wait_locator_visible(
                self.DOWNLOAD_MENU_ITEM, MENU_READY_TIMEOUT_MS
            ):
                print(f"  ⚠ [{index}] 未找到「下载」菜单项")
                return False

            download_btn = self.page.locator(self.DOWNLOAD_MENU_ITEM).first
            async with self.page.expect_download() as download_info:
                await download_btn.click()

            download = await download_info.value
            print(f"  [{index}] 等待下载完成…")
            temp_path = await download.path()
            filename = f"{index}_{download.suggested_filename}"
            final_path = os.path.join(download_dir, filename)
            shutil.move(temp_path, final_path)

            size_kb = os.path.getsize(final_path) / 1024
            print(f"  ✅ [{index}] {filename} ({size_kb:.2f} KB)")
            return True

        except Exception as exc:
            print(f"  ❌ [{index}] 失败: {exc}")
            err_img = os.path.join(download_dir, f"error_{index}.png")
            await self.page.screenshot(path=err_img)
            print(f"  📷 [{index}] 截图: {err_img}")
            return False
