#!/usr/bin/env bash
# macOS 打包 — 须在 Mac 上执行:
#   cd tencent_docs_pom && chmod +x build/build.sh && ./build/build.sh
# 精简版（不含浏览器）:
#   ./build/build.sh --lite

set -euo pipefail

LITE=0
if [[ "${1:-}" == "--lite" || "${1:-}" == "-Lite" ]]; then
  LITE=1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RELEASE_DIR="$ROOT/releases"
DIST="$ROOT/dist"
ZIP_NAME="WorkOrderAutomation-macOS.zip"
if [[ "$LITE" -eq 1 ]]; then
  ZIP_NAME="WorkOrderAutomation-macOS-lite.zip"
fi

echo "==> pip install"
python3 -m pip install -q -r requirements.txt

if [[ "$LITE" -eq 0 ]]; then
  echo "==> playwright install chromium --no-shell"
  python3 -m playwright install chromium --no-shell
fi

echo "==> PyInstaller"
python3 -m PyInstaller build/tencent_docs.spec --noconfirm --clean

EXE="$DIST/WorkOrderAutomation"
if [[ ! -f "$EXE" ]]; then
  echo "未找到 $EXE" >&2
  exit 1
fi
chmod +x "$EXE"

# data 模板
rm -rf "$DIST/data"
mkdir -p "$DIST/data"
for f in data/*; do
  base="$(basename "$f")"
  [[ "$base" == "session.json" ]] && continue
  cp "$f" "$DIST/data/"
done

if [[ "$LITE" -eq 1 ]]; then
  rm -rf "$DIST/ms-playwright"
  echo "==> Lite：不打包 ms-playwright"
else
  echo "==> 复制 Chromium"
  python3 build/stage_browsers.py "$DIST"
fi

rm -rf "$DIST/app.log" "$DIST/templates" 2>/dev/null || true

cat > "$DIST/使用说明.txt" <<'EOF'
录音师工单自动化 — macOS 版

1. 解压后保持 WorkOrderAutomation、data、ms-playwright 在同一文件夹。
2. 首次打开若提示无法验证，请在「系统设置 → 隐私与安全性」中允许。
3. 也可在终端执行: chmod +x WorkOrderAutomation && ./WorkOrderAutomation
4. 首次使用需微信扫码登录；会话在 data/session.json。
EOF

mkdir -p "$RELEASE_DIR"
ZIP_PATH="$RELEASE_DIR/$ZIP_NAME"
rm -f "$ZIP_PATH"
(
  cd "$DIST"
  zip -r "$ZIP_PATH" . -x "*.DS_Store"
)

TOTAL=$(du -sk "$DIST" | awk '{print $1}')
echo ""
echo "DONE dist: $DIST"
echo "DONE zip:  $ZIP_PATH  (约 $((TOTAL / 1024)) MB 解压后)"
