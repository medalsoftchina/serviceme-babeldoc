#!/bin/bash

NUM_WORKERS=1

for ((i=1; i<=NUM_WORKERS; i++)); do
  # 正确设置环境变量并启动celery worker
  MACHINE_ID="${i}" /app/.venv/bin/python -m celery -A tasks.celery_app.app worker -Q translate;
done