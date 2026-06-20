# 打包与分发说明

> **推荐：** Nuitka + UPX 轻量化方案见 [docs/PACKAGING_NUITKA.md](docs/PACKAGING_NUITKA.md)

## 体积说明

| 版本 | Windows zip | 说明 |
|------|-------------|------|
| **标准版** | `releases/WorkOrderAutomation-Windows.zip` | 含 Chromium（`--no-shell`），约 **480MB**，离线可用 |
| **Lite 版** | `releases/WorkOrderAutomation-Windows-lite.zip` | 仅 exe + 配置，约 **85MB**，首次运行联网下载浏览器 |

旧包同时含 `chromium` + `chromium_headless_shell`（约 650MB 浏览器），已去掉 headless_shell。

---

## Windows（在本机执行）

```powershell
cd tencent_docs_pom
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

Lite 精简包：

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1 -Lite
```

产物：`releases/WorkOrderAutomation-Windows.zip` 与 `dist/` 文件夹。

---

## macOS（须在苹果电脑上执行）

```bash
cd tencent_docs_pom
chmod +x build/build.sh
./build/build.sh
```

Lite：`./build/build.sh --lite`

产物：`releases/WorkOrderAutomation-macOS.zip`

> PyInstaller 无法跨平台：Windows 包只能在本机打，Mac 包只能在 Mac 上打。

---

## 发给别人的内容

解压 zip 后整个文件夹一起使用：

| 路径 | 说明 |
|------|------|
| `WorkOrderAutomation` / `WorkOrderAutomation.exe` | 主程序 |
| `data/` | 配置（不要分发 `session.json`） |
| `ms-playwright/` | Chromium（标准版已含；Lite 首次运行自动生成） |

---

## 开发机运行（不打包）

```bash
pip install -r requirements.txt
playwright install chromium --no-shell
python run.py
```

上级目录需存在 `app.py`（汇总计税逻辑）。
