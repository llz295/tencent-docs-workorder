"""Nuitka 构建脚本 - 直接使用 Python 执行，避免 PowerShell 编码问题"""
import subprocess
import sys
import os
import shutil

ROOT = os.getcwd()
NUITKA_OUT = os.path.join(ROOT, "build", "nuitka-out")
APP_DIST = os.path.join(ROOT, "dist", "WorkOrderAutomation")
RELEASE_DIR = os.path.join(ROOT, "releases")


def clean():
    """清理旧的构建产物"""
    dirs = [
        NUITKA_OUT,
        APP_DIST,
        os.path.join(ROOT, "run.build"),
        os.path.join(ROOT, "run.dist"),
        os.path.join(ROOT, "run.onefile-build"),
        os.path.join(ROOT, "nuitka-crash-report.xml"),
    ]
    for d in dirs:
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"  removed: {d}")
        elif os.path.isfile(d):
            os.remove(d)
            print(f"  removed: {d}")


def prepare_vendor():
    """准备 vendor/app.py"""
    vendor_dir = os.path.join(ROOT, "vendor")
    os.makedirs(vendor_dir, exist_ok=True)
    dest = os.path.join(vendor_dir, "app.py")
    # 检查 vendor/app.py 是否已存在
    if os.path.isfile(dest):
        print(f"  vendor/app.py 已存在: {dest}")
        return
    # 检查上级目录或当前目录的 app.py
    for path in [os.path.join(ROOT, "..", "app.py"), os.path.join(ROOT, "app.py")]:
        if os.path.isfile(path):
            shutil.copy2(path, dest)
            print(f"  已复制: {path} -> {dest}")
            return
    print("  vendor/app.py 不需要复制（已存在或不适用）")


def run_nuitka():
    """执行 Nuitka 编译"""
    # 本机空闲内存有限：gcc 在 -O3 下编译 playwright 等大文件时单进程可占 ~2GB。
    # 并行度过高会导致内存耗尽、gcc 被杀而编译失败（原脚本用 --jobs=1 即为此）。
    # 折中用 2 个并行 + --low-memory，比串行快、又不爆内存。
    jobs = "2"
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        # 保留控制台：Web 工具需要显示访问地址，崩溃时也能看到报错
        # （原来的 --windows-console-mode=disable 会让程序崩溃时窗口一闪即逝）
        "--windows-console-mode=force",
        f"--output-dir={NUITKA_OUT}",
        "--output-filename=WorkOrderAutomation.exe",
        "--mingw64",
        f"--jobs={jobs}",
        # 降低 C 编译阶段的内存占用，避免并行 gcc 把内存打爆
        "--low-memory",
        "--company-name=WorkOrderAutomation",
        "--product-name=WorkOrderAutomation",
        "--file-version=1.0.0.0",
        "--product-version=1.0.0.0",
        "--include-package=playwright",
        # Playwright 启动浏览器依赖 driver(node.exe + CLI)，必须一并打包
        "--include-package-data=playwright",
        "--include-package=pandas",
        "--include-package=openpyxl",
        "--include-package=fastapi",
        "--include-package=uvicorn",
        "--include-package=starlette",
        "--include-package=flask",
        # SSL 证书（requests / playwright 下载都需要）
        "--include-package-data=certifi",
        "--include-package=config",
        "--include-package=auth",
        "--include-package=pages",
        "--include-package=services",
        "--include-package=core",
        "--include-package=summarize",
        "--include-package=web",
        "--include-package=vendor",
        "--include-module=app",
        f"--include-data-dir={os.path.join(ROOT, 'data')}=data",
        f"--include-data-dir={os.path.join(ROOT, 'web', 'static')}=web/static",
        f"--include-data-dir={os.path.join(ROOT, 'vendor')}=vendor",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=IPython",
        "--nofollow-import-to=jupyter",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=sklearn",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=tensorflow",
        "--nofollow-import-to=PyQt5",
        "--nofollow-import-to=PyQt6",
        "--nofollow-import-to=PySide2",
        "--nofollow-import-to=PySide6",
        "--nofollow-import-to=wx",
        "--nofollow-import-to=pandas.tests",
        "--nofollow-import-to=PyInstaller",
        "--nofollow-import-to=playwright._impl.__pyinstaller",
        os.path.join(ROOT, "run.py"),
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(ROOT, "vendor") + ";" + ROOT
    # 设置 SSL 证书
    try:
        import certifi
        env["SSL_CERT_FILE"] = certifi.where()
        env["REQUESTS_CA_BUNDLE"] = certifi.where()
    except ImportError:
        pass

    print("Starting Nuitka compile...")
    sys.stdout.flush()

    r = subprocess.run(cmd, cwd=ROOT, env=env)
    if r.returncode != 0:
        print(f"Nuitka compile failed with code {r.returncode}")
        sys.exit(1)
    print("Nuitka compile completed!")


def find_built_dir():
    """查找编译输出目录"""
    built_dir = os.path.join(NUITKA_OUT, "run.dist")
    if os.path.isdir(built_dir):
        return built_dir
    # 尝试查找其他 .dist 目录
    if os.path.isdir(NUITKA_OUT):
        for name in os.listdir(NUITKA_OUT):
            if name.endswith(".dist"):
                return os.path.join(NUITKA_OUT, name)
    print(f"Error: Nuitka output directory not found in {NUITKA_OUT}")
    sys.exit(1)


def stage_dist(built_dir):
    """整理 dist 文件夹"""
    if os.path.isdir(APP_DIST):
        shutil.rmtree(APP_DIST)
    shutil.copytree(built_dir, APP_DIST)
    print(f"  dist staged: {APP_DIST}")

    # 复制 data 配置文件（排除 session 和 lock 文件）
    data_src = os.path.join(ROOT, "data")
    data_dst = os.path.join(APP_DIST, "data")
    if os.path.isdir(data_dst):
        shutil.rmtree(data_dst)
    os.makedirs(data_dst, exist_ok=True)
    exclude = {"session.json", "instance.lock", "session.json.bak"}
    for fname in os.listdir(data_src):
        if fname not in exclude:
            src = os.path.join(data_src, fname)
            if os.path.isfile(src):
                shutil.copy2(src, data_dst)
    print(f"  data config copied to {data_dst}")


def copy_browser():
    """复制 Chromium 浏览器到 dist"""
    browsers_src = os.path.join(ROOT, "ms-playwright")
    browsers_dst = os.path.join(APP_DIST, "ms-playwright")
    if os.path.isdir(browsers_dst):
        shutil.rmtree(browsers_dst)

    if not os.path.isdir(browsers_src):
        print("  ms-playwright not found in project, skipping browser copy")
        return

    # 查找 Chromium 目录
    chromium_dir = None
    for name in os.listdir(browsers_src):
        if name.startswith("chromium-") and "headless_shell" not in name:
            exe = os.path.join(browsers_src, name, "chrome-win64", "chrome.exe")
            if os.path.isfile(exe):
                chromium_dir = name
                break
            # 也检查 chrome-win 目录
            exe = os.path.join(browsers_src, name, "chrome-win", "chrome.exe")
            if os.path.isfile(exe):
                chromium_dir = name
                break

    if chromium_dir:
        print(f"  Found Chromium: {chromium_dir}")
        shutil.copytree(
            os.path.join(browsers_src, chromium_dir),
            os.path.join(browsers_dst, chromium_dir),
        )
        # 复制 Playwright 运行所需的辅助组件：ffmpeg（录屏）、winldd（依赖检查）
        for name in os.listdir(browsers_src):
            if name.startswith(("ffmpeg-", "winldd-")):
                shutil.copytree(
                    os.path.join(browsers_src, name),
                    os.path.join(browsers_dst, name),
                )
                print(f"  copied helper: {name}")
        # 复制 .links 目录
        links_src = os.path.join(browsers_src, ".links")
        if os.path.isdir(links_src):
            shutil.copytree(links_src, os.path.join(browsers_dst, ".links"))
        print(f"  Chromium copied to dist")
    else:
        print("  No Chromium found in ms-playwright, skipping browser copy")


def copy_vc_runtime():
    """复制 VC++ 运行时 DLL"""
    dlls = ["msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "concrt140.dll"]
    sys32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
    for dll in dlls:
        src = os.path.join(sys32, dll)
        dst = os.path.join(APP_DIST, dll)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            print(f"  {dll} copied")
        else:
            print(f"  Warning: {dll} not found in System32")


def create_release_zip():
    """创建发布 zip 包"""
    os.makedirs(RELEASE_DIR, exist_ok=True)
    zip_name = "WorkOrderAutomation-Windows.zip"
    zip_path = os.path.join(RELEASE_DIR, zip_name)
    if os.path.isfile(zip_path):
        os.remove(zip_path)

    # 使用 shutil 创建 zip
    shutil.make_archive(
        os.path.join(RELEASE_DIR, "WorkOrderAutomation-Windows"),
        "zip",
        os.path.dirname(APP_DIST),
        os.path.basename(APP_DIST),
    )

    # 计算大小
    total_size = 0
    for root, dirs, files in os.walk(APP_DIST):
        for f in files:
            fpath = os.path.join(root, f)
            total_size += os.path.getsize(fpath)
    total_mb = round(total_size / 1024 / 1024, 1)

    exe_path = os.path.join(APP_DIST, "WorkOrderAutomation.exe")
    exe_size = round(os.path.getsize(exe_path) / 1024 / 1024, 1) if os.path.isfile(exe_path) else 0

    print(f"\n========================================")
    print(f" DONE")
    print(f" App folder: {APP_DIST}")
    print(f" Release:    {zip_path}")
    print(f" exe size:   {exe_size} MB")
    print(f" total:      {total_mb} MB")
    print(f"========================================")


def main():
    print("========================================")
    print(" Nuitka build - WorkOrderAutomation")
    print("========================================")

    print("\n[0/7] Clean stale build artifacts")
    clean()

    print("\n[1/7] Prepare vendor/app.py")
    prepare_vendor()

    print("\n[2/7] Nuitka compile (standalone)")
    run_nuitka()

    print("\n[3/7] Find built directory")
    built_dir = find_built_dir()
    print(f"  Built dir: {built_dir}")

    print("\n[4/7] Stage dist folder")
    stage_dist(built_dir)

    print("\n[5/7] Copy Chromium to dist")
    copy_browser()

    print("\n[6/7] Copy VC++ runtime DLLs")
    copy_vc_runtime()

    print("\n[7/7] Create release zip")
    create_release_zip()


if __name__ == "__main__":
    main()
