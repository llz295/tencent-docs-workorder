# Nuitka 打包 · 完整分步教程

用 Nuitka 把项目编译成 Windows 原生可执行程序，`--standalone` 输出一个自带运行时的文件夹，
连同 Chromium 一起分发，接收方无需安装 Python。

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

### 1.1 克隆项目并建虚拟环境

```powershell
git clone <仓库地址>
cd yuandaima
python -m venv .venv311
.venv311\Scripts\activate
```

### 1.2 安装依赖

```powershell
pip install -r requirements-build.txt
```

### 1.3 准备浏览器内核

仓库不含 `ms-playwright/`（太大）。首次打包前先下载 Chromium 到项目内：

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\ms-playwright"
python -m playwright install chromium --no-shell
```

打包脚本会把该目录里的 Chromium 拷进产物；若不存在则跳过，程序首次运行时会联网自动下载。

### 1.4 准备 vendor/app.py

`vendor/app.py` 是汇总/计税逻辑。仓库已包含则无需处理；缺失时把上级目录的 `app.py`
复制到 `vendor/app.py` 即可（`do_build.py` 也会自动尝试复制）。

---

## 二、一键打包

```powershell
python build\do_build.py
```

脚本自动执行 7 步：

| 步骤 | 内容 |
|------|------|
| 0/7 | 清理旧的构建产物 |
| 1/7 | 准备 `vendor/app.py` |
| 2/7 | Nuitka `--standalone` 编译 `run.py`（多核并行） |
| 3/7 | 定位编译输出目录 |
| 4/7 | 整理到 `dist/WorkOrderAutomation/` 并复制 `data/` 配置 |
| 5/7 | 复制 Chromium（含 ffmpeg/winldd）到 `ms-playwright/` |
| 6/7 | 复制 VC++ 运行时 DLL |
| 7/7 | 生成 `releases/WorkOrderAutomation-Windows.zip` |

编译耗时约 **10~30 分钟**（取决于 CPU），首次更慢。

---

## 三、产物说明

解压 `releases/WorkOrderAutomation-Windows.zip` 后：

```
WorkOrderAutomation/
├── WorkOrderAutomation.exe   # 主程序（启动器，约 20MB 属正常）
├── *.dll / *.pyd             # 运行时依赖（python311.dll 等）
├── data/                     # 配置文件（可编辑，不含 session.json）
├── ms-playwright/            # Chromium（标准版）
├── web/static/               # 网页版前端
└── vendor/                   # 汇总/计税逻辑
```

> **为什么 exe 只有 20 多 MB？** `--standalone` 模式下 exe 只是启动器，真正的代码和依赖以
> `python311.dll`、各种 `.pyd` 独立文件放在同一文件夹。**必须整个文件夹一起分发**，
> 不能只发 exe。想要单文件用 `--onefile`，但本项目带 400MB Chromium 不适合（启动慢）。

**使用：** 双击 `WorkOrderAutomation.exe` 启动网页版，或命令行：

```powershell
WorkOrderAutomation.exe            # 网页版（默认）
WorkOrderAutomation.exe download   # 仅下载
WorkOrderAutomation.exe summarize  # 仅汇总
WorkOrderAutomation.exe all        # 下载并汇总
```

---

## 四、关键 Nuitka 参数（build/do_build.py）

| 参数 | 作用 |
|------|------|
| `--standalone` | 独立目录分发，不依赖本机 Python |
| `--mingw64` | 使用 MinGW 编译，生成原生二进制 |
| `--jobs=<CPU核数>` | 多核并行编译，加速 |
| `--windows-console-mode=force` | **保留控制台**：显示访问地址，崩溃时能看到报错 |
| `--include-package=playwright` | 打包 Playwright；Nuitka 插件会自动带上 driver 与浏览器信息 |
| `--include-package=fastapi/uvicorn/starlette/flask` | Web 服务依赖 |
| `--include-package=pandas/openpyxl` | 数据处理 |
| `--include-module=app` | 编入 vendor 汇总逻辑 |
| `--include-data-dir` | 打包 `data/`、`web/static/`、`vendor/` |
| `--nofollow-import-to=...` | 剔除 matplotlib/torch 等无用库，减小体积 |

---

## 五、⚠️ 不要使用 UPX

早期版本用 `upx --best --lzma` 二次压缩 exe/dll，会导致：

- 压缩 `python311.dll` / `.pyd` → **程序启动即崩溃**；
- 压缩 Chromium 的 `chrome.exe` 及其 DLL → **浏览器无法启动**；
- 更容易被杀毒软件误报。

配合 `--windows-console-mode=disable` 时崩溃连报错都看不到，表现为「双击没反应 / 无法运行」。
因此当前打包流程**已彻底移除 UPX**。根目录保留的 `upx.exe` 仅作备用，不参与打包。

---

## 六、发布到 GitHub Releases

源码可用仓库自带脚本推送（需先安装 Git 并配置身份）：

```powershell
powershell -ExecutionPolicy Bypass -File build\publish_github.ps1 -RepoUrl "https://github.com/<用户名>/<仓库>.git"
```

发布二进制：

1. 在 GitHub 创建 Release（如 `v1.0.0`）；
2. 上传 `releases/WorkOrderAutomation-Windows.zip`；
3. README 的 Releases 链接指向该 zip。

**不要**把 `releases/`、`dist/`、`ms-playwright/`、`data/session.json` 提交进 Git（已在 `.gitignore`）。

---

## 七、故障排查

| 现象 | 处理 |
|------|------|
| 双击 exe 没反应 / 一闪而过 | 确认用的是当前 `do_build.py`（控制台保留），在控制台看报错 |
| Nuitka 找不到 MinGW | 加 `--assume-yes-for-downloads`（脚本已含），或手动安装 MinGW64 |
| 汇总报错 No module named 'app' | 确认 `vendor/app.py` 存在 |
| 打包后 Playwright 找不到浏览器 | 确认 `ms-playwright/` 与 exe 同级、含 `chromium-*` |
| exe 被杀毒误报 | 添加白名单或对 exe 做代码签名 |

---

## 八、手动分步（等价于脚本）

```powershell
pip install -r requirements-build.txt

$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\ms-playwright"
python -m playwright install chromium --no-shell

python -m nuitka --standalone --mingw64 --windows-console-mode=force `
  --include-package=playwright --include-package=pandas --include-package=openpyxl `
  --include-package=fastapi --include-package=uvicorn --include-package=starlette --include-package=flask `
  --include-package=config --include-package=auth --include-package=pages `
  --include-package=services --include-package=core --include-package=summarize `
  --include-package=web --include-package=vendor --include-module=app `
  --include-data-dir=data=data --include-data-dir=web/static=web/static --include-data-dir=vendor=vendor `
  --output-dir=build/nuitka-out --output-filename=WorkOrderAutomation.exe `
  run.py

# 然后把 build/nuitka-out/run.dist 拷到 dist/WorkOrderAutomation，
# 并复制 data/、ms-playwright/ 到同级目录。直接用 do_build.py 会自动完成这些。
```
