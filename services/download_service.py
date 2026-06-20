"""异步并发批量下载（失败自动重试直至全部成功）。"""
import asyncio
import json
from pathlib import Path
from typing import List, Tuple

from config.download_settings import DownloadConfig
from config.settings import DOC_URLS_PATH, DOWNLOAD_DIR, RETRY_ROUND_DELAY_SEC
from pages.sheet_page import SheetPage
from playwright.async_api import BrowserContext

DocTask = Tuple[int, dict]


class DownloadService:
    def __init__(self, context: BrowserContext, config: DownloadConfig):
        self._context = context
        self._config = config
        self._log_lock = asyncio.Lock()

    @staticmethod
    def load_doc_list() -> list:
        with open(DOC_URLS_PATH, encoding="utf-8") as f:
            return json.load(f)

    async def _log(self, message: str) -> None:
        async with self._log_lock:
            print(message)

    async def _download_one(
        self,
        semaphore: asyncio.Semaphore,
        index: int,
        item: dict,
        download_dir: str,
        total: int,
        *,
        retry_round: int = 0,
    ) -> bool:
        async with semaphore:
            name = item.get("name", "")
            url = item["url"]
            if retry_round > 0:
                await self._log(
                    f"=== 重试 第{retry_round}轮 {index}/{total} {name} ==="
                )
            else:
                await self._log(f"=== 开始 {index}/{total} {name} ===")

            page = await self._context.new_page()
            try:
                sheet = SheetPage(page)
                return await sheet.download_sheet(
                    url=url,
                    download_dir=download_dir,
                    index=index,
                    label=name,
                )
            finally:
                await page.close()

    async def _run_batch(
        self,
        pending: List[DocTask],
        semaphore: asyncio.Semaphore,
        download_dir: str,
        total: int,
        retry_round: int = 0,
    ) -> List[DocTask]:
        """执行一批下载，返回仍失败的 (index, item) 列表。"""
        results = await asyncio.gather(
            *[
                self._download_one(
                    semaphore,
                    index,
                    item,
                    download_dir,
                    total,
                    retry_round=retry_round,
                )
                for index, item in pending
            ],
            return_exceptions=True,
        )

        failed: List[DocTask] = []
        for (index, item), result in zip(pending, results):
            if isinstance(result, Exception):
                name = item.get("name", "")
                await self._log(f"  ❌ [{index}] {name} 异常: {result}")
                failed.append((index, item))
            elif not result:
                failed.append((index, item))

        return failed

    async def run_all(self) -> None:
        docs = self.load_doc_list()
        download_dir = Path(DOWNLOAD_DIR)
        download_dir.mkdir(parents=True, exist_ok=True)
        concurrency = self._config.concurrency
        total = len(docs)

        print(f"📁 下载目录: {download_dir}")
        print(f"📋 共 {total} 个文档")
        print(f"⚡ 并发数: {concurrency}")
        print("🔁 失败文档将自动重试，直至全部成功\n")

        pending: List[DocTask] = [(i, item) for i, item in enumerate(docs, 1)]
        semaphore = asyncio.Semaphore(concurrency)
        retry_round = 0

        while pending:
            if retry_round > 0:
                names = "、".join(item.get("name", str(idx)) for idx, item in pending)
                print(
                    f"\n🔄 第 {retry_round} 轮重试（{len(pending)} 个）: {names}"
                )
                print(f"   {RETRY_ROUND_DELAY_SEC} 秒后开始…")
                await asyncio.sleep(RETRY_ROUND_DELAY_SEC)

            pending = await self._run_batch(
                pending,
                semaphore,
                str(download_dir),
                total,
                retry_round=retry_round,
            )
            retry_round += 1

        print(f"\n🎉 全部 {total} 个文档均已下载成功！")
