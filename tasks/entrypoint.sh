#!/bin/bash

# -----------------------------
# 清理现有 celery 进程和临时文件
# -----------------------------
echo "Clearing celery processes and temporary files"
pkill -9 -f "celery" || true
rm -f /tmp/worker_*.state /tmp/celery* 2>/dev/null || true
sleep 3

## -----------------------------
## 启动 beat
## -----------------------------
#echo "Starting beat"
#celery -A tasks.celery_app.app beat &
#sleep 5

# -----------------------------
# 启动默认 CPU worker (prefork)
# -----------------------------
echo "Starting default worker"
WORKER_NAME=default celery -A tasks.celery_app.app worker -P prefork -Q default -n default@%h --loglevel=info &
sleep 8

## -----------------------------
## 启动 IO worker (gevent)
## -----------------------------
#echo "Starting io worker (gevent)"
#WORKER_NAME=io python tasks/io_worker.py &
#sleep 5

## -----------------------------
## 启动 Flower
## -----------------------------
#echo "Starting Flower on port 5333"
#celery -A tasks.celery_app.app flower --port=5333 --address=0.0.0.0

# -----------------------------
# 捕获退出信号清理后台进程
# -----------------------------
trap "pkill -P $$" EXIT
