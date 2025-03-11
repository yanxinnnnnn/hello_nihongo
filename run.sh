#!/bin/bash

# 启动脚本: run.sh
# 用于在服务器上启动或停止 hello_nihongo 项目

# 设置项目目录
PROJECT_DIR=$(cd "$(dirname "$0")"; pwd)

# 设置日志文件路径
LOG_FILE="$PROJECT_DIR/logs/server.log"
PID_FILE="$PROJECT_DIR/pid.txt"

# 确保日志目录存在
mkdir -p $(dirname $LOG_FILE)

start() {
    echo "启动 FastAPI 服务器..."

    # 进入项目目录
    cd $PROJECT_DIR

    # 激活虚拟环境
    source venv/bin/activate

    # 启动 FastAPI 服务
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > $LOG_FILE 2>&1 &

    # 获取进程 ID 并保存到文件
    echo $! > "$PID_FILE"

    echo "服务器已启动，日志输出到 $LOG_FILE"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "停止服务器 (PID: $PID)..."
            kill "$PID"
            rm -f "$PID_FILE"
            echo "服务器已停止。"
        else
            echo "进程 $PID 未运行，清理 PID 文件。"
            rm -f "$PID_FILE"
        fi
    else
        echo "未找到 PID 文件，服务器可能未运行。"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "用法: $0 {start|stop}"
        exit 1
        ;;
esac