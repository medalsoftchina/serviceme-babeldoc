#!/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : extra_config.py
Time       ：2025/7/28 17:09
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
import os
import socket
import sys

from conf.conf import REDIS_URL

is_redis_cluster = os.environ.get("LANGFLOW_REDIS_CLUSTER", "false").lower() == "true"


def add_socket_config(broker_transport_options: dict):
    """
    socket 相关配置
    """
    socket_keepalive_options = {
        socket.TCP_KEEPINTVL: 30,  # keepalive探测间隔(秒)
        socket.TCP_KEEPCNT: 3,  # 探测失败重试次数
    }

    if sys.platform.startswith("linux"):
        # Linux系统特定的TCP keepalive选项
        socket_keepalive_options[socket.TCP_KEEPIDLE] = 60
    else:
        socket_keepalive_options[socket.TCP_KEEPALIVE] = 60

    additional_config = {
        "visibility_timeout": 3600,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
        "redis_max_connections": 10,
        "socket_keepalive": True,
        "health_check_interval": 30,  # 健康检查间隔
        "socket_keepalive_options": socket_keepalive_options,
    }

    # 更新配置
    broker_transport_options.update(additional_config)
    return broker_transport_options


def add_redis_cluster_config(broker_transport_options: dict):
    result_backend_transport_options = None
    broker_use_ssl, redis_backend_use_ssl = None, None

    if is_redis_cluster:
        # 集群模式特定配置
        cluster_config = {
            "queue_order_strategy": "priority",
            # 使用哈希标签确保所有键都在同一个槽位
            "global_keyprefix": "{celery}:",
            "sep": ".",
            "prefix": "{celery}:",
            "key_prefix": "{celery}:",
            "fanout_prefix": True,
            "fanout_patterns": True,
            "unpack_pattern": True,
            "visibility_timeout": 43200,
            "lock_timeout": 3600,
            "max_connections": 100,
            "socket_connect_timeout": 30,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }

        broker_transport_options.update(cluster_config)

        # 结果后端的集群配置
        result_backend_transport_options = {
            "global_keyprefix": "{celery}:",
            "retry_on_timeout": True,
            "cluster_mode": True,
            "key_prefix": "{celery}:",
            "retry_policy": {
                "max_retries": 3,
                "interval_start": 0,
                "interval_step": 2,
                "interval_max": 6,
            },
        }

        # SSL 配置
        if "rediss" in REDIS_URL:
            ssl_config = {"ssl_cert_reqs": "required"}
            broker_transport_options.update(ssl_config)
            result_backend_transport_options.update(ssl_config)

    return (
        broker_transport_options,
        result_backend_transport_options,
        broker_use_ssl,
        redis_backend_use_ssl,
    )
