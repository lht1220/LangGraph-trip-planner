#!/bin/bash
# 多Agent智能旅行助手 - 一键停止
# 用法: 在 Git Bash 中运行  ./stop.sh  或  bash stop.sh

stop_port() {
    local port="$1"
    local name="$2"
    echo "停止 $name (端口 $port) ..."
    local pid
    pid=$(netstat -ano | grep ":$port " | grep LISTENING | awk '{print $5}' | head -1)
    if [ -n "$pid" ]; then
        powershell -Command "Stop-Process -Id $pid -Force" 2>/dev/null
        echo "  已停止 PID $pid"
    else
        echo "  $name 未在运行"
    fi
}

echo "============================================"
echo "  多Agent智能旅行助手 - 一键停止"
echo "============================================"
echo ""

stop_port 8000 "后端"
stop_port 5173 "前端"

echo ""
echo "完成。"
