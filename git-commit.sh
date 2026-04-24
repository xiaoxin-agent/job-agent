#!/usr/bin/env bash
# git-commit.sh — 先跑测试，全过才 commit
# 用法: bash git-commit.sh "commit message"
set -euo pipefail

cd "$(dirname "$0")"

MSG="${1:-}"
if [ -z "$MSG" ]; then
    echo "❌ 用法: bash git-commit.sh \"commit message\""
    exit 1
fi

echo "🧪 运行测试..."
if python3 tests.py 2>&1; then
    echo "✅ 所有测试通过"
else
    echo "❌ 测试失败，中止 commit"
    exit 1
fi

git add -A
git commit -m "$MSG"
echo "✅ 提交完成"
