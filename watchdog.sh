#!/bin/bash
# 求职Agent - 看门狗脚本
# 由cron每分钟调用一次，崩了自动重启
#
# 注意：cron 环境不会继承交互式终端的 DEEPSEEK_API_KEY。
# 启动前显式加载 OpenClaw 的 gateway.systemd.env（含 DEEPSEEK_API_KEY），
# 否则服务起来后 AI 功能会报“缺少 DeepSeek API Key”。

cd /home/ubuntu/.openclaw/workspace/job-agent

# 加载运行所需的环境变量（文件权限 600，只读不打印）
ENV_FILE="$HOME/.openclaw/gateway.systemd.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
else
    echo "[$(date)] ⚠️  未找到 $ENV_FILE，AI 功能可能不可用" >> watchdog.log
fi

if ! curl -sf http://localhost:9999/ > /dev/null 2>&1; then
    echo "[$(date)] ❌ 服务无响应，正在重启..." >> watchdog.log
    bash agent_ctl.sh start >> watchdog.log 2>&1
    echo "[$(date)] ✅ 重启完成" >> watchdog.log
fi
