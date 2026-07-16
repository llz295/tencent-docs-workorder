# 腾讯文档 · 录音师工单自动化

批量下载腾讯文档录音师工单，并生成薪资结算 Excel（主表 / 结算汇总 / 终表 / 分段主表）。

支持 **命令行** 和 **网页版（局域网可访问）** 两种使用方式。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 批量下载 | 并发拉取 `doc_urls.json` 中全部工单，失败自动重试 |
| 登录探针 | 快速校验 session；失效自动有头扫码，扫码成功后无头继续 |
| 工单汇总 | 读取本地 xlsx，生成结算表；支持日历多时间段（闭区间） |
| 网页版 | FastAPI + 纯 JS UI，支持 `0.0.0.0` 局域网多人访问 |
| 关闭即退 | 关闭所有浏览器标签页后，服务进程自动在 3 秒内退出 |
| 单实例 | 不允许重复启动，关闭后重新运行即可再次打开 |

---

## 快速开始（源码运行）

### 环境要求

- Windows 10/11（推荐）
- Python 3.10+
- 微信（腾讯文档扫码登录）

### 安装

```powershell
git clone https://github.com/<用户名>/yuandaima.git
cd yuandaima

python -m venv .venv311
.venv311\Scripts\activate

pip install -r requirements.txt
playwright install chromium --no-shell
```

### 启动网页版（默认）

```powershell
python run.py
```

直接无参数运行，自动启动网页版并在浏览器中打开 `http://127.0.0.1:8765/`。

终端会同时打印本机地址和**局域网地址**，同事直接复制局域网链接在浏览器中打开即可。

### 命令行模式

```powershell
python run.py --web          # 显式启动网页版
python run.py download       # 仅批量下载（CLI，无网页）
python run.py summarize      # 仅汇总
python run.py all            # 下载并汇总
python run.py download -w 2  # 指定并发数（默认 5）
```

---

## 局域网共享使用

1. 确认 `data/app_config.json` 中 `"web_host": "0.0.0.0"`（默认即是）
2. 在**服务器电脑**运行 `python run.py`
3. 终端输出类似：
   ```
   本机访问: http://127.0.0.1:8765/
   局域网访问（其他电脑浏览器打开以下地址）:
     http://192.168.1.100:8765/
   ```
4. 同事直接复制 `http://192.168.1.100:8765/` 在浏览器中打开即可

> **防火墙提示：** 若局域网无法访问，在 Windows 防火墙放行 TCP 入站端口 `8765`。

---

## 关闭与重启

- **关闭**：直接关闭所有浏览器标签页（叉掉网页），服务进程在 3 秒内自动退出
- **重启**：再次运行 `python run.py`（或双击 `WorkOrderAutomation.exe`）即可重新打开

---

## 直接运行（免安装 Python）

从 GitHub **Releases** 下载 zip，解压后双击 `WorkOrderAutomation.exe`。

自行打包：

```powershell
python build\do_build.py
# 产物: dist/WorkOrderAutomation/  与  releases/WorkOrderAutomation-Windows.zip
```

> 打包推荐 Python 3.11；详见 [PACKAGING.md](PACKAGING.md)

---

## 网页版菜单说明

| 一级 | 二级 | 说明 |
|------|------|------|
| 工作台 | 一键执行 | 批量下载 / 工单汇总 / 下载并汇总（三个独立按钮） |
| 下载 | 并发与重试 | 并发数、重试间隔 |
| 下载 | 浏览器 | 无头模式、浏览器通道 |
| 汇总 | 交互流程 | 确认弹窗、Sheet 选择、日历 |
| 汇总 | 输出设置 | 文件名前缀、固定工作表 |
| 汇总 | 价格表 | 化名映射与单价 |
| 路径 | 目录 | 下载目录、输出目录 |
| 路径 | 登录 | 探针 URL、探针超时、扫码超时、网页版绑定地址/端口 |
| 文档 | 录音师列表 | `doc_urls.json`（录音师姓名 + 文档链接） |
| 系统 | 配置文件 / 超时 / 运行日志 | 实时日志查看 |

---

## 配置文件

| 文件 | 说明 |
|------|------|
| `data/app_config.json` | 路径、超时、浏览器、网页版绑定（`web_host` / `web_port`） |
| `data/download_config.json` | 下载并发数 |
| `data/summarize_config.json` | 汇总流程与输出 |
| `data/voice_actor_config.json` | 录音师化名与单价 |
| `data/doc_urls.json` | 腾讯文档 URL 列表 |
| `data/session.json` | 登录会话（自动生成，**请勿分享**） |

---

## 打包（Nuitka standalone）

### 前置

1. `vendor/app.py`（汇总核心逻辑）已包含在仓库中，无需额外准备
2. 首次打包前下载浏览器内核到项目内：
   ```powershell
   $env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\ms-playwright"
   python -m playwright install chromium --no-shell
   ```

### 一键打包

```powershell
python build\do_build.py
```

编译耗时约 10~30 分钟。完整教程见 [docs/PACKAGING_NUITKA.md](docs/PACKAGING_NUITKA.md)。

### 产物

| 路径 | 说明 |
|------|------|
| `dist/WorkOrderAutomation/` | 可直接运行的完整目录（**整个文件夹一起分发**） |
| `releases/WorkOrderAutomation-Windows.zip` | 发布 zip（约 260MB，含 Chromium） |

> `WorkOrderAutomation.exe` 本身约 20MB 属正常：standalone 模式下它只是启动器，
> 依赖以独立文件放在同一文件夹。**不要用 UPX 压缩产物**，会导致 exe 或浏览器无法启动。

---

## 上传到 GitHub

### 1. 初始化仓库

```powershell
cd yuandaima
git init
git add .
git commit -m "feat: 录音师工单自动化（网页版 + Nuitka 打包）"
git branch -M main
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

### 2. 发布 Release（附带 exe zip）

1. 本地执行 `python build\do_build.py` 生成 zip
2. GitHub → **Releases → Draft a new release**
3. 上传 `releases/WorkOrderAutomation-Windows.zip`

### 3. 不要提交的内容

已在 `.gitignore` 中排除：`ms-playwright/`、`dist/`、`releases/`、`data/session.json` 等。

`upx.exe` 已提交到仓库（约 600KB），当前打包流程未使用，仅作备用。

---

## 目录结构

```
yuandaima/
├── run.py                 # 唯一入口（无参数=启动网页版）
├── upx.exe                # UPX 工具（备用，打包流程未使用）
├── requirements.txt       # 运行依赖
├── requirements-build.txt # 打包依赖
├── web/                   # 网页版（FastAPI + static）
│   ├── server.py          # REST API + SSE 日志推送
│   └── static/            # index.html / app.js / app.css
├── core/                  # 下载/汇总流程编排
├── auth/                  # 登录态管理（扫码/session）
├── pages/                 # Page Object Model（Playwright）
├── services/              # 并发批量下载服务
├── summarize/             # 工单汇总与 Excel 生成
├── config/                # 配置加载模块
├── data/                  # 运行时 JSON 配置
├── vendor/app.py          # 汇总核心逻辑（打包依赖）
└── build/
    ├── do_build.py        # Nuitka 一键打包（唯一打包脚本）
    └── publish_github.ps1 # 推送源码到 GitHub
```

---

## 常见问题

**Q: 探针失败 / 需要扫码？**  
A: 会话过期会自动打开有头浏览器扫码；扫码成功后关闭有头，无头继续下载。

**Q: 网页版局域网打不开？**  
A: 确认 `web_host=0.0.0.0`，并在 Windows 防火墙放行 TCP 端口 `8765`（入站规则）。

**Q: 关闭浏览器后服务没退出？**  
A: 服务在所有标签页断开后等待 3 秒再退出，属正常现象。若仍未退出可在终端按 Ctrl+C。

**Q: 打包后汇总报错？**  
A: 确认 `vendor/app.py` 存在（仓库已包含）。

**Q: 能否多人同时操作？**  
A: 可以同时打开网页查看状态和日志，但任务同一时间只能运行一个（后端有任务锁）。

---

## License

[MIT](LICENSE)
