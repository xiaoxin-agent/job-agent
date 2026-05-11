#!/bin/bash
# Package the extension as a .zip for easy distribution
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$SCRIPT_DIR/save-job-extension"
OUTPUT="$SCRIPT_DIR/job-saver-extension.zip"

cd "$EXT_DIR"

# Remove old package
rm -f "$OUTPUT"

# Create zip (exclude .git, node_modules, etc.)
zip -r "$OUTPUT" . \
  -x ".git/*" \
  -x "*.gitignore" \
  -x "*.DS_Store" \
  -x "*.md"

echo "✅ Packaged: $OUTPUT"
echo "   Size: $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "📦 To install in Chrome:"
echo "   1. chrome://extensions → 开发者模式"
echo "   2. 加载已解压的扩展程序 → 选择: $EXT_DIR"
echo ""
echo "   或者把 zip 发给别人，解压后按同样步骤安装。"
