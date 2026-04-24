#!/bin/bash
# 求职Agent - 管理脚本
# 支持: start / stop / restart / status / test / watchdog

cd "$(dirname "$0")"
PID_FILE="agent_web.pid"
LOG_FILE="agent_web.log"

start() {
    if pgrep -f "python3 job_agent_web.py" > /dev/null; then
        echo "✅ 已在运行 (PID: $(pgrep -f 'job_agent_web.py' | head -1))"
        return 0
    fi
    
    echo "🚀 启动..."
    nohup python3 job_agent_web.py > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 等待启动确认
    sleep 2
    if pgrep -f "job_agent_web.py" > /dev/null; then
        echo "✅ 启动成功 (PID: $pid)"
        echo "🌐 http://localhost:9999"
        return 0
    else
        echo "❌ 启动失败，查看日志: tail -f $LOG_FILE"
        return 1
    fi
}

stop() {
    local stopped=false
    
    # 从PID文件停
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill "$pid" 2>/dev/null; then
            stopped=true
        fi
        rm -f "$PID_FILE"
    fi
    
    # 兜底：杀所有进程
    pids=$(pgrep -f "python3.*job_agent_web" 2>/dev/null)
    if [ -n "$pids" ]; then
        kill $pids 2>/dev/null
        stopped=true
    fi
    
    if $stopped; then
        echo "✅ 已停止"
    else
        echo "ℹ️ 没有运行中的进程"
    fi
}

status() {
    local pid
    pid=$(pgrep -f "python3.*job_agent_web" | head -1)
    
    if [ -n "$pid" ]; then
        local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
        echo "✅ 运行中"
        echo "   PID: $pid"
        echo "   运行时间: $uptime"
        echo "   端口: 9999"
        echo "   日志: tail -f $LOG_FILE"
        return 0
    else
        echo "❌ 未运行"
        return 1
    fi
}

test() {
    echo "🧪 运行测试..."
    python3 tests.py
    return $?
}

watchdog() {
    # 看门狗: 检查是否在运行，不在则重启
    if ! pgrep -f "python3.*job_agent_web" > /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ 进程不在，正在重启..."
        start
    fi
}

case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    test)
        test
        ;;
    watchdog)
        watchdog
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|test|watchdog}"
        echo ""
        echo "  start     启动服务"
        echo "  stop      停止服务"
        echo "  restart   重启服务"
        echo "  status    查看状态"
        echo "  test      运行测试套件"
        echo "  watchdog  一键检查/重启 (可用于cron)"
        exit 1
        ;;
esac