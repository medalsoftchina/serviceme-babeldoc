# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : celery_app.py
Time       ：2025/6/12 10:45
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
from datetime import timedelta
from enum import Enum

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init
from kombu import Exchange
from kombu import Queue
import os
from pathlib import Path
from loguru import logger

from app.common.engine.pg_session import get_db_session
from app.common.log import register_logger
from app.model.attachment_storage.attachment_storage import AttachmentStorage
from datetime import datetime

class QueueName(Enum):
    # 默认
    DEFAULT = "translate"


def make_celery():
    app = Celery("serviceme")

    # load config
    app.config_from_object("tasks.celery_config.conf")

    # log
    machine_id = os.environ.get("MACHINE_ID")
    ROBOT_DATA_PATH = os.environ.get("LANGFLOW_ROBOT_DATA_PATH")
    if ROBOT_DATA_PATH:
        if not machine_id:
            log_path = Path(ROBOT_DATA_PATH) / "backend" / "translate.log"
        else:
            log_path = Path(ROBOT_DATA_PATH) / "backend" / f"translate_{machine_id}.log"
        register_logger(log_path=log_path)
    else:
        current_file_dir = os.path.dirname(os.path.abspath(__file__))

        # 获取 src 的绝对路径
        src_dir = os.path.join(current_file_dir, "../../../")

        # 拼接 robot_data 路径，与 src 平级
        robot_data_path = os.path.join(src_dir, "../robot_data")

        # 规范化路径（消除多余的分隔符）
        robot_data_path = os.path.normpath(robot_data_path)
        if not machine_id:
            log_path = Path(robot_data_path) / "backend" / "celery.log"
        else:
            log_path = Path(robot_data_path) / "backend" / f"celery_{machine_id}.log"
        register_logger(log_path=log_path)
    return app


app = make_celery()

app.conf.update(
    # define routes
    task_routes={
        "translate": {"queue": QueueName.DEFAULT.value},
    },
    # define queues
    task_queues=[
        Queue(
            QueueName.DEFAULT.value,
            exchange=Exchange(QueueName.DEFAULT.value, type="direct"),
            routing_key=QueueName.DEFAULT.value,
        )
    ],
    task_default_queue=QueueName.DEFAULT.value,
    task_default_exchange=QueueName.DEFAULT.value,
    task_default_routing_key=QueueName.DEFAULT.value,
)

app.autodiscover_tasks(
    [
        "tasks.task.task",
    ]
)

@worker_init.connect
def worker_init(**kwargs):
    try:
        # todo 更新文件状态
        with get_db_session() as session:
            files = (
                AttachmentStorage.query(session)
                    .filter(AttachmentStorage.status.in_([4, 5]))
                    .all()
            )
            for file in files:
                file.error_message = "system restart"
                file.updated_at = datetime.utcnow()
                file.status = 6
            session.commit()
        logger.info("celery worker [Startup Hook] init complete")
    except Exception as e:
        logger.error(f"celery worker startup connect redis error: {e}")
        return
