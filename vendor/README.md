# vendor

汇总模块依赖 `app.py`（Excel 计税与主表生成逻辑）。

## 来源

打包脚本 `build/prepare_vendor.py` 会自动从以下位置复制：

1. 上级目录 `../app.py`（开发环境）
2. 若已存在 `vendor/app.py` 则直接使用

## 手动放置

若仓库中不含 `app.py`，请将汇总逻辑文件复制为本目录下的 `app.py` 后再打包。

```powershell
copy ..\app.py vendor\app.py
```
