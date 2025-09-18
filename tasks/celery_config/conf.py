# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : celery_config.py
Time       ：2025/6/12 10:22
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
import os

from conf.conf import REDIS_URL
from conf.conf import IO_WORKER_CONCURRENCY
from conf.conf import LOG_LEVEL
from conf.conf import TZ
from conf.conf import WORKER_CONCURRENCY
from conf.conf import WORKER_MAX_TASKS_PER_CHILD
from tasks.celery_config.extra_config import add_redis_cluster_config
from tasks.celery_config.extra_config import add_socket_config

# [logger level]
loglevel = LOG_LEVEL  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# [broker && backend]
broker_url = REDIS_URL
result_backend = REDIS_URL

# broker retry config
broker_connection_retry_on_startup = True

# 任务优先级设置
task_priority_steps = list(range(10))
task_default_priority = 5

# 序列化配置
accept_content = ["json"]
task_serializer = "json"
result_serializer = "json"
result_accept_content = ["json"]
timezone = TZ
enable_utc = True

# 任务结果过期时间
result_expires = 60 * 60

# 工作进程配置
worker_name = os.getenv("WORKER_NAME", "default")
if worker_name == "default":
    worker_concurrency = WORKER_CONCURRENCY
    worker_max_tasks_per_child = WORKER_MAX_TASKS_PER_CHILD
    worker_prefetch_multiplier = 1
    # 防止 worker 通信问题
    worker_proc_alive_timeout = 120.0  # 等待 worker 进程 UP 消息的超时时间
    worker_process_start_timeout = 120.0  # 进程启动超时时间
    worker_pool_putlocks = True
    worker_pool_restarts = True
    # 任务执行时间限制
    task_time_limit = 60 * 60
    task_soft_time_limit = 60 * 60


elif worker_name == "io":
    worker_concurrency = IO_WORKER_CONCURRENCY
    worker_proc_alive_timeout = 120.0
    worker_process_start_timeout = 120.0

    # 任务执行时间限制保留
    task_time_limit = 60 * 60
    task_soft_time_limit = 60 * 60

# Notion: prefork 模式时，定义 worker_max_tasks_per_child 数量，防止内存泄漏和回收资源，应使用下列配置，这是 kombu 兼容性问题
# 当前 celery=5.4.0, kombu=5.5.3(5.3.1)
# issues for resolve -> [Timed out waiting for UP message from <ForkProcess>]
# refers: issues: [https://github.com/celery/kombu/issues/1785]
broker_transport_options = {
    "socket_timeout": 30,
    "socket_connect_timeout": 30,  # 连接超时
    "visibility_timeout": 3600,
}
broker_transport_options.update(add_socket_config(broker_transport_options))

(
    _broker_transport_options,
    _result_backend_transport_options,
    _broker_use_ssl,
    _redis_backend_use_ssl,
) = add_redis_cluster_config(broker_transport_options)

if _broker_transport_options:
    broker_transport_options.update(_broker_transport_options)

if _result_backend_transport_options:
    result_backend_transport_options = _result_backend_transport_options

if _broker_use_ssl:
    broker_use_ssl = _broker_use_ssl

if _redis_backend_use_ssl:
    redis_backend_use_ssl = _redis_backend_use_ssl

# 日志配置
worker_hijack_root_logger = False
worker_log_color = False

# beat with redis
# redbeat_lock_key = "redbeat:lock"
# redbeat_lock_timeout = 60
# beat_scheduler = "redbeat.RedBeatScheduler"
# redbeat_redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{CELERY_BROKER_DB}"

worker_name = os.getenv("WORKER_NAME")
worker_state_db = f"/tmp/worker_{worker_name}.state"

# 禁用 pid 文件
worker_pidfile = None
