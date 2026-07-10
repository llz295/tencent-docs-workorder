"""一二三级菜单结构定义。"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class MenuLevel3:
    key: str
    title: str


@dataclass(frozen=True)
class MenuLevel2:
    key: str
    title: str
    panel: str
    sections: List[MenuLevel3] = field(default_factory=list)


@dataclass(frozen=True)
class MenuLevel1:
    key: str
    title: str
    children: List[MenuLevel2]


APP_MENU: List[MenuLevel1] = [
    MenuLevel1(
        "workbench",
        "工作台",
        [
            MenuLevel2(
                "workbench.run",
                "一键执行",
                "dashboard",
                [MenuLevel3("actions", "快捷操作")],
            ),
        ],
    ),
    MenuLevel1(
        "download",
        "下载",
        [
            MenuLevel2(
                "download.concurrency",
                "并发与重试",
                "download",
                [
                    MenuLevel3("concurrency", "并发数量"),
                    MenuLevel3("retry", "失败重试"),
                ],
            ),
            MenuLevel2(
                "download.browser",
                "浏览器",
                "download_browser",
                [
                    MenuLevel3("headless", "运行模式"),
                    MenuLevel3("channel", "浏览器通道"),
                ],
            ),
        ],
    ),
    MenuLevel1(
        "summarize",
        "汇总",
        [
            MenuLevel2(
                "summarize.flow",
                "交互流程",
                "summarize",
                [
                    MenuLevel3("prompts", "弹窗与确认"),
                    MenuLevel3("sheet", "工作表选择"),
                    MenuLevel3("calendar", "时间段日历"),
                ],
            ),
            MenuLevel2(
                "summarize.output",
                "输出设置",
                "summarize_output",
                [
                    MenuLevel3("prefix", "文件名"),
                    MenuLevel3("sheet_fixed", "固定工作表"),
                ],
            ),
            MenuLevel2(
                "summarize.pricing",
                "价格表",
                "pricing",
                [
                    MenuLevel3("mapping", "化名→实名"),
                    MenuLevel3("prices", "全新/补录单价"),
                ],
            ),
        ],
    ),
    MenuLevel1(
        "paths",
        "路径",
        [
            MenuLevel2(
                "paths.dirs",
                "目录",
                "paths",
                [
                    MenuLevel3("download_dir", "工单下载目录"),
                    MenuLevel3("output_dir", "汇总输出目录"),
                ],
            ),
            MenuLevel2(
                "paths.login",
                "登录",
                "paths_login",
                [
                    MenuLevel3("probe", "探测表格 URL"),
                    MenuLevel3("timeout", "扫码超时"),
                ],
            ),
        ],
    ),
    MenuLevel1(
        "docs",
        "文档",
        [
            MenuLevel2(
                "docs.list",
                "录音师列表",
                "docs",
                [MenuLevel3("urls", "文档 URL 列表")],
            ),
        ],
    ),
    MenuLevel1(
        "system",
        "系统",
        [
            MenuLevel2(
                "system.config_files",
                "配置文件",
                "config_files",
                [MenuLevel3("list", "路径与打开编辑")],
            ),
            MenuLevel2(
                "system.timeouts",
                "超时",
                "advanced",
                [
                    MenuLevel3("editor", "编辑器就绪"),
                    MenuLevel3("menu", "菜单就绪"),
                    MenuLevel3("sheet", "表格加载"),
                ],
            ),
            MenuLevel2(
                "system.log",
                "运行日志",
                "log",
                [MenuLevel3("console", "实时日志")],
            ),
        ],
    ),
]


def find_level2(key: str) -> Optional[MenuLevel2]:
    for l1 in APP_MENU:
        for l2 in l1.children:
            if l2.key == key:
                return l2
    return None
