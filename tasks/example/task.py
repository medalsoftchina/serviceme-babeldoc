# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : task.py
Time       ：2025/6/23 09:22
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
import time

from app.common.engine.pg_session import get_db_session
from app.common.log import logger
from tasks.celery_app import app


@app.task(name="add_task")
def add(x, y):
    logger.info(f"add {x} and {y}")
    # with session commit
    time.sleep(2)
    logger.info("result = %s" % (x + y))
    return x + y


@app.task(name="simple_test")
def simple_test():
    print("Simple test task executed!")
    return "OK"


@app.task(name="how_to_use_sync_session")
def how_to_use_sync_session():
    with get_db_session() as db_session:
        db_session.execute(...)
        # do something with db_session
        # something_svc.get_something
        pass
