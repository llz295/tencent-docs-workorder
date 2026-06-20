# 腾讯文档 · 录音师工单自动化

批量下载腾讯文档录音师工单，并生成薪资结算 Excel（主表 / 结算汇总 / 终表 / 分段主表）。

支持 **桌面 GUI**、**命令行**、**网页版（局域网可访问）** 三种使用方式。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 批量下载 | 并发拉取 `doc_urls.json` 中全部工单，失败自动重试 |
| 登录探针 | 快速校验 session；失效自动有头扫码，扫码后无头继续 |
| 工单汇总 | 读取本地 xlsx，生成结算表；支持日历多时间段（闭区间） |
| 桌面 GUI | CustomTkinter 一二三级菜单，全配置可视化 |
| 网页版 | FastAPI + 同款 UI，支持 `0.0.0.0` 局域网访问 |
| 单实例 | 桌面版与网页版互斥，不可同时运行 |

---

## 快速开始（源码运行）

### 环境要求

- Windows 10/11（推荐）
- Python 3.10+
- 微信（腾讯文档扫码登录）

### 安装

```powershell
git clone https://github.com/llz295/tencent-docs-workorder.git
cd tencent_docs_pom

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium --no-shell
python build\prepare_vendor.py
python run.py
```

首次运行会弹出 **桌面 / 网页版** 选择（可在配置中记住）。

### 命令行

```powershell
python run.py --gui          # 桌面 GUI
python run.py --web          # 网页版（默认 http://127.0.0.1:8765）
python run.py download       # 仅下载
python run.py summarize      # 仅汇总
python run.py all            # 下载并汇总
python run.py download -w 2  # 指定并发
```

### 局域网网页版

1. **路径 → 登录 → 网页版绑定地址** 设为 `0.0.0.0`
2. `python run.py --web`
3. 终端会打印 `http://<局域网IP>:8765/`，其他电脑浏览器打开即可

---

## 直接运行（免安装 Python）

从 GitHub **Releases** 下载 zip，解压后双击 `WorkOrderAutomation.exe`。

自行打包：

```powershell
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1
# 产物: dist/WorkOrderAutomation/  与  releases/*.zip
```

> 打包推荐 Python 3.11；详见 [docs/PACKAGING_NUITKA.md](docs/PACKAGING_NUITKA.md)

---

## 图形界面菜单

| 一级 | 二级 | 说明 |
|------|------|------|
| 工作台 | 一键执行 | 下载 / 汇总 / 下载并汇总 |
| 下载 | 并发与重试 | 并发数、重试间隔 |
| 下载 | 浏览器 | 无头模式、浏览器通道 |
| 汇总 | 交互流程 | 确认弹窗、Sheet、日历 |
| 汇总 | 输出设置 | 文件名前缀、固定工作表 |
| 汇总 | 价格表 | 化名映射与单价 |
| 路径 | 目录 | 下载目录、输出目录 |
| 路径 | 登录 | 探针 URL、探针超时、扫码超时、启动方式 |
| 文档 | 录音师列表 | `doc_urls.json` |
| 系统 | 配置文件 / 超时 / 运行日志 | |

---

## 配置文件

| 文件 | 说明 |
|------|------|
| `data/app_config.json` | 路径、超时、浏览器、网页版绑定 |
| `data/download_config.json` | 下载并发 |
| `data/summarize_config.json` | 汇总流程与输出 |
| `data/voice_actor_config.json` | 录音师化名与单价 |
| `data/doc_urls.json` | 腾讯文档 URL 列表 |
| `data/session.json` | 登录会话（自动生成，勿分享） |

---

## 打包（Nuitka + UPX 方案一）

**优势：** 编译为原生二进制，体积更小、内存占用更低；UPX 二次压缩 exe/dll。

### 前置

1. 项目根目录放置 `upx.exe`（你已准备好）
2. 执行 `python build\prepare_vendor.py`（自动复制 `vendor/app.py`）

### 一键打包

```powershell
# 标准版（含 Chromium）
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1

# Lite 版（首次运行下载浏览器）
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1 -Lite

# 跳过 UPX
powershell -ExecutionPolicy Bypass -File build\nuitka_build.ps1 -SkipUpx
```

### 产物

| 路径 | 说明 |
|------|------|
| `dist/WorkOrderAutomation/` | 可直接运行的完整目录 |
| `releases/WorkOrderAutomation-Nuitka-Windows.zip` | 分发 zip |

详细分步说明见 [docs/PACKAGING_NUITKA.md](docs/PACKAGING_NUITKA.md)。

### 备选：PyInstaller

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

见 [PACKAGING.md](PACKAGING.md)。

---

## 上传 GitHub

### 1. 初始化仓库

```powershell
cd tencent_docs_pom
git init
git add .
git commit -m "feat: 录音师工单自动化（GUI + 网页版 + Nuitka 打包）"
git branch -M main
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

### 2. 发布 Release（附带 exe）

1. 本地执行 `build\nuitka_build.ps1` 生成 zip
2. GitHub → **Releases → Draft a new release**
3. 上传 `releases/WorkOrderAutomation-Nuitka-Windows.zip`
4. 可选再上传 Lite 版

### 3. 不要提交的内容

已在 `.gitignore` 中排除：`ms-playwright/`、`dist/`、`releases/`、`session.json` 等。

`upx.exe` 可提交到仓库（体积约 500KB），也可由协作者自行放置。

---

## 目录结构

```
tencent_docs_pom/
├── run.py                 # 唯一入口
├── upx.exe                # UPX 压缩工具（打包用）
├── ui/                    # 桌面 GUI
├── web/                   # 网页版（FastAPI + static）
├── core/                  # 下载/汇总编排
├── auth/ pages/ services/ # 登录与 POM
├── summarize/             # 汇总与日历
├── config/                # 配置加载
├── data/                  # 运行时 JSON 配置
├── vendor/app.py          # 汇总核心逻辑（打包依赖）
├── build/
│   ├── nuitka_build.ps1   # Nuitka 一键打包
│   ├── apply_upx.ps1      # UPX 二次压缩
│   ├── prepare_vendor.py  # 复制 app.py
│   └── build.ps1          # PyInstaller 打包
└── docs/PACKAGING_NUITKA.md
```

---

## 常见问题

**Q: 探针失败 / 需要扫码？**  
A: 会话过期会自动打开有头浏览器扫码；扫码成功后关闭有头，无头继续下载。

**Q: 网页版局域网打不开？**  
A: 确认 `web_host=0.0.0.0`，防火墙放行 TCP 8765。

**Q: 打包后汇总报错？**  
A: 确认 `vendor/app.py` 存在（运行 `python build/prepare_vendor.py`）。

**Q: 桌面版和网页版能同时开吗？**  
A: 不能，单实例锁会阻止。

---

## License

[MIT](LICENSE)
