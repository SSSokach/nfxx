#!/bin/bash
# 后台启动后端服务

cd "$(dirname "$0")/backend"

if [ -f nohup.pid ] && kill -0 "$(cat nohup.pid)" 2>/dev/null; then
    echo "后端服务已在运行中 (PID: $(cat nohup.pid))"
    exit 1
fi

nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
echo $! > nohup.pid
echo "后端服务已启动 (PID: $(cat nohup.pid))，日志: backend.log"
