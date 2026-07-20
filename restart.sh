#!/bin/bash
# 重启后端服务

cd "$(dirname "$0")/backend"

if [ -f nohup.pid ] && kill -0 "$(cat nohup.pid)" 2>/dev/null; then
    echo "正在停止后端服务 (PID: $(cat nohup.pid))..."
    kill "$(cat nohup.pid)"
    sleep 2
    # 如果进程还在，强制终止
    if kill -0 "$(cat nohup.pid)" 2>/dev/null; then
        kill -9 "$(cat nohup.pid)"
    fi
    rm -f nohup.pid
    echo "后端服务已停止"
else
    echo "后端服务未在运行"
fi

nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
echo $! > nohup.pid
echo "后端服务已重启 (PID: $(cat nohup.pid))，日志: backend.log"
