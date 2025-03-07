#!/bin/bash

# 启动脚本: run.sh
# 用于在服务器上启动 hello_nihongo 项目

# 设置项目目录
PROJECT_DIR=$(cd "$(dirname "$0")"; pwd)

# 进入项目目录
cd $PROJECT_DIR

# 激活虚拟环境
source venv/bin/activate

# 设置日志文件路径
LOG_FILE="$PROJECT_DIR/logs/server.log"

# 确保日志目录存在
mkdir -p $(dirname $LOG_FILE)

# 启动 FastAPI 服务
echo "启动 FastAPI 服务器..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > $LOG_FILE 2>&1 &

# 获取进程 ID 并保存到文件
echo $! > "$PROJECT_DIR/pid.txt"

echo "服务器已启动，日志输出到 $LOG_FILE"