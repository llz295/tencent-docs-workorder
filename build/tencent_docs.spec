# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：在 tencent_docs_pom 目录执行 build\\build.ps1 或 build/build.sh"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

SPEC_DIR = Path(SPECPATH)
POM_DIR = SPEC_DIR.parent
AUTO_DIR = POM_DIR.parent

_is_win = sys.platform.startswith("win")
_is_mac = sys.platform == "darwin"
_exe_name = "WorkOrderAutomation"

datas = [
    (str(POM_DIR / "data"), "data"),
    (str(AUTO_DIR / "app.py"), "."),
]

# 仅打包 Playwright 驱动（浏览器放 exe 旁 ms-playwright，不塞进 exe）
import playwright as _pw

_pw_driver = Path(_pw.__file__).resolve().parent / "driver"
if _pw_driver.is_dir():
    datas.append((str(_pw_driver), "playwright/driver"))

binaries = []
hiddenimports = (
    collect_submodules("playwright")
    + collect_submodules("customtkinter")
    + collect_submodules("ui")
    + collect_submodules("summarize")
    + collect_submodules("config")
    + collect_submodules("auth")
    + collect_submodules("pages")
    + collect_submodules("services")
    + collect_submodules("core")
)
hiddenimports += [
    "playwright._impl._api_structures",
    "playwright._impl._driver",
    "playwright.__main__",
    "pandas",
    "openpyxl",
    "app",
    "summarize.app_bridge",
    "config.voice_actor_pricing",
    "config.playwright_bootstrap",
]

tmp = collect_all("customtkinter")
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

a = Analysis(
    [str(POM_DIR / "run.py")],
    pathex=[str(POM_DIR), str(AUTO_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(SPEC_DIR / "runtime_hook_playwright.py")],
    excludes=[
        "matplotlib",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "scipy",
        "sklearn",
        "torch",
        "tensorflow",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=_exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=_is_mac,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
