# 打包与分发说明

> 打包方案：**Nuitka `--standalone`**。完整分步教程见 [docs/PACKAGING_NUITKA.md](docs/PACKAGING_NUITKA.md)。

## 体积说明

| 版本 | Windows zip | 说明 |
|------|-------------|------|
| **标准版** | `releases/WorkOrderAutomation-Windows.zip` | 含 Chromium（`--no-shell`），约 **260MB**，离线可用 |

> `WorkOrderAutomation.exe` 本身约 20MB 是正常的：`--standalone` 模式下 exe 只是启动器，
> 依赖以独立文件放在同一文件夹，**必须整个文件夹一起分发**。

---

## Windows 打包（在本机执行）

```powershell
cd yuandaima
.venv311\Scripts\activate

# 首次：下载浏览器内核到项目内（仓库不含，太大）
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\ms-playwright"
python -m playwright install chromium --no-shell

# 一键打包
python build\do_build.py
```

产物：`releases/WorkOrderAutomation-Windows.zip` 与 `dist/WorkOrderAutomation/` 文件夹。

---

## 发给别人的内容

解压 zip 后**整个文件夹**一起使用：

| 路径 | 说明 |
|------|------|
| `WorkOrderAutomation.exe` | 主程序（双击启动网页版） |
| `data/` | 配置（不要分发 `session.json`） |
| `ms-playwright/` | Chromium（标准版已含） |
| `web/static/`、`vendor/` | 前端与汇总逻辑 |

---

## 开发机运行（不打包）

```bash
pip install -r requirements.txt
playwright install chromium --no-shell
python run.py
```

`vendor/app.py`（汇总计税逻辑）需存在。
