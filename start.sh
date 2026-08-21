#!/bin/bash
# 多Agent智能旅行助手 - 一键启动
# 用法: 在 Git Bash 中运行  ./start.sh  或  bash start.sh

cd "$(dirname "$0")"

echo "============================================"
echo "  多Agent智能旅行助手 - 一键启动"
echo "============================================"
echo ""

# 启动后端（8000）
echo "[1/2] 启动后端 http://localhost:8000 ..."
(cd backend && py -3.14 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000) > backend.log 2>&1 &
echo "      日志写入 backend.log"

# 启动前端（5173）
echo "[2/2] 启动前端 http://localhost:5173 ..."
(cd frontend && npm run dev) > frontend.log 2>&1 &
echo "      日志写入 frontend.log"

echo ""
echo "已后台启动。"
echo "  后端文档: http://localhost:8000/docs"
echo "  前端页面: http://localhost:5173"
echo ""
echo "查看日志: tail -f backend.log   或   tail -f frontend.log"
echo "停止服务: ./stop.sh"
