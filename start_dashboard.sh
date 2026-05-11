#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-${1:-8000}}"
LOG_DIR="$PROJECT_ROOT/.tmp"
LOG_PATH="$LOG_DIR/dashboard.log"
DASHBOARD_URL="http://${HOST}:${PORT}/"

mkdir -p "$LOG_DIR"

existing_pids="$(lsof -ti "tcp:${PORT}" || true)"
if [ -n "$existing_pids" ]; then
    echo "端口 ${PORT} 已被占用，先停止旧进程: ${existing_pids}"
    kill $existing_pids || true
    sleep 1

    remaining_pids="$(lsof -ti "tcp:${PORT}" || true)"
    if [ -n "$remaining_pids" ]; then
        echo "旧进程未退出，强制停止: ${remaining_pids}"
        kill -9 $remaining_pids || true
        sleep 1
    fi
fi

echo "启动 Dashboard 服务..."
nohup python3 -c "from app.dashboard_server import serve_dashboard; serve_dashboard(host='${HOST}', port=${PORT})" \
    >"$LOG_PATH" 2>&1 &
server_pid=$!

for _ in $(seq 1 50); do
    if curl -fsS "$DASHBOARD_URL" >/dev/null 2>&1; then
        echo "dashboard=${DASHBOARD_URL}"
        echo "pid=${server_pid}"
        echo "log=${LOG_PATH}"
        exit 0
    fi

    if ! kill -0 "$server_pid" >/dev/null 2>&1; then
        echo "Dashboard 启动失败，请检查日志: ${LOG_PATH}" >&2
        tail -n 50 "$LOG_PATH" >&2 || true
        exit 1
    fi

    sleep 0.2
done

echo "Dashboard 启动超时，请检查日志: ${LOG_PATH}" >&2
exit 1
