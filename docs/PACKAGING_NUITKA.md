# Nuitka 极致轻量化打包 · 完整分步教程

方案一：Nuitka 编译 + UPX 二次压缩，相比 PyInstaller 体积更小、运行时内存更低。

---

## 一、环境准备

| 项目 | 要求 |
|------|------|
| 系统 | Windows 10/11 x64 |
| Python | **3.10 ~ 3.12（推荐 3.11）** |
| 编译器 | 3.12 及以下自动用 MinGW64；3.13+ 需安装 **Visual Studio Build Tools** |
| 磁盘 | 至少 3GB 空闲（含 Chromium） |
| 网络 | 首次需下载 Nuitka 依赖；无本地浏览器时需下载 Chromium |

> Python 3.13/3.14 仅实验性支持，编译慢且可能失败，**强烈建议使用 3.11**。

### 1.1 克隆项目

```powershell
git clone <仓库地址>
cd tencent_docs_pom
python -m venv .venv
.venv\Scripts\activate
```

### 1.2 安装依赖

```powershell
pip install -r requirements-build.txt
```

### 1.3 放置 UPX

将 `upx.exe` 放在项目根目录（与 `run.py` 同级）。  
脚本也会查找 `tools/upx.exe` 或系统 PATH 中的 `upx`。

### 1.4 准备 vendor/app.py

```powershell
python build\prepare_vendor.py
```

从上级 `app.py` 复制汇总逻辑到 `vendor/app.py`（GitHub 仓库已含则可跳过）。

---

## 二、一键打包

```powershell
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1
```

脚本自动执行 8 步：

| 步骤 | 内容 |
|------|------|
| 1/8 | 安装 pip 依赖 + Nuitka |
| 2/8 | 准备 vendor/app.py |
| 3/8 | `playwright install chromium --no-shell` |
| 4/8 | Nuitka `--standalone` 编译 `run.py` |
| 5/8 | 整理到 `dist/WorkOrderAutomation/` |
| 6/8 | 复制 `data/` 配置、Chromium 到 `ms-playwright/` |
| 7/8 | UPX `--best --lzma` 压缩 exe/dll |
| 8/8 | 生成 `releases/*.zip` |

### Lite 版（不含浏览器）

```powershell
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1 -Lite
```

首次运行程序时会联网下载 Chromium（约 400MB）。

### 跳过 UPX

```powershell
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1 -SkipUpx
```

---

## 三、产物说明

解压 `releases/WorkOrderAutomation-Nuitka-Windows.zip` 后：

```
WorkOrderAutomation/
├── WorkOrderAutomation.exe   # 主程序（UPX 压缩后）
├── *.dll                     # 运行时依赖
├── data/                     # 配置文件（可编辑）
├── ms-playwright/            # Chromium（标准版）
├── web/static/               # 网页版前端
└── README-win.txt
```

**使用：** 双击 `WorkOrderAutomation.exe`，或命令行：

```powershell
WorkOrderAutomation.exe --web
WorkOrderAutomation.exe download
```

---

## 四、Nuitka 参数说明（build/nuitka_build.ps1）

| 参数 | 作用 |
|------|------|
| `--standalone` | 独立目录分发，不依赖本机 Python |
| `--mingw64` | 使用 MinGW 编译，生成原生二进制 |
| `--lto=yes` | 链接时优化，减小体积 |
| `--enable-plugin=tk-inter` | 打包 Tkinter/CustomTkinter |
| `--windows-console-mode=disable` | GUI 模式无黑窗口 |
| `--include-module=app` | 编入 vendor 汇总逻辑 |
| `--include-data-dir` | 打包 data/、web/static/ |
| `--nofollow-import-to=...` | 剔除 matplotlib 等无用库 |

---

## 五、UPX 压缩

`build/apply_upx.ps1` 对 `dist/` 内 exe/dll 执行：

```powershell
upx.exe --best --lzma --force <文件>
```

- **跳过：** `ms-playwright/` 内浏览器文件
- **跳过：** `python*.dll`、`vcruntime` 等系统运行时（避免兼容问题）
- 主程序 `WorkOrderAutomation.exe` 通常可压缩 **50%+**

---

## 六、发布到 GitHub Releases

1. 本地打包完成后，在 GitHub 创建 Release（如 `v1.0.0`）
2. 上传 `releases/WorkOrderAutomation-Nuitka-Windows.zip`
3. README 中 Releases 链接指向该 zip

**不要** 把 `releases/`、`dist/`、`ms-playwright/` 提交进 Git（已在 `.gitignore`）。

---

## 七、与 PyInstaller 对比

| 对比项 | Nuitka（本方案） | PyInstaller |
|--------|------------------|-------------|
| 原理 | Python → C → 原生二进制 | 打包字节码 + 引导器 |
| exe 体积 | 更小（+ UPX 更小） | 较大 |
| 运行内存 | 更低 | 较高 |
| 编译时间 | 较长（5~20 分钟） | 较短 |
| 脚本 | `build/nuitka_build.ps1` | `build/build.ps1` |

---

## 八、故障排查

| 现象 | 处理 |
|------|------|
| Nuitka 找不到 MinGW | 加 `--assume-yes-for-downloads`，或手动安装 MinGW64 |
| 汇总报错 No module named 'app' | 运行 `python build/prepare_vendor.py` |
| 打包后 Playwright 找不到浏览器 | 确认 `ms-playwright/` 与 exe 同级 |
| UPX 后程序无法启动 | 使用 `-SkipUpx` 重新打包 |
| exe 被杀毒误报 | Nuitka+UPX 可能被误报，添加白名单或代码签名 |

---

## 九、手动分步（等价于脚本）

```powershell
pip install -r requirements-build.txt
python build\prepare_vendor.py
playwright install chromium --no-shell

$env:PYTHONPATH = "vendor;."
python -m nuitka --standalone --mingw64 --enable-plugin=tk-inter `
  --windows-console-mode=disable --include-module=app `
  --include-data-dir=data=data --include-data-dir=web/static=web/static `
  --output-dir=build/nuitka-out --output-filename=WorkOrderAutomation.exe `
  run.py

# 复制 run.dist 到 dist/WorkOrderAutomation
python build/stage_browsers.py dist/WorkOrderAutomation
powershell -File build/apply_upx.ps1 -TargetDir dist/WorkOrderAutomation
```
