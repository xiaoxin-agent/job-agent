#!/bin/bash
# 求职Agent - 看门狗脚本
# 由cron每分钟调用一次，崩了自动重启

cd /home/ubuntu/.openclaw/workspace/job-agent

if ! curl -sf http://localhost:9999/ > /dev/null 2>&1; then
    echo "[$(date)] ❌ 服务无响应，正在重启..." >> watchdog.log
    bash agent_ctl.sh start >> watchdog.log 2>&1
    echo "[$(date)] ✅ 重启完成" >> watchdog.log
fi