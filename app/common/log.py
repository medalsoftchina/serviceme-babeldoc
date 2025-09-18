#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: tyrone
File: log.py
Time: 2025/5/12
"""
import logging
import os
import re
import sys
from loguru import logger as lg_logger
from conf.conf import LOG_LEVEL

# 获取默认日志路径（如果未指定则使用此路径）
ROBOT_DATA_PATH = os.environ.get("LANGFLOW_ROBOT_DATA_PATH")
DEFAULT_LOG_FILE_PATH = os.path.join(ROBOT_DATA_PATH, "backend",
                                     "translate.log") if ROBOT_DATA_PATH else "translate.log"
os.makedirs(os.path.dirname(DEFAULT_LOG_FILE_PATH), exist_ok=True)


class InterceptHandler(logging.Handler):
    """
    Remove log colors to prevent formatting issues

    Some framework methods may generate colored logs that could cause processing errors when handled by loguru.
    This handler is essential to ensure proper log writing by stripping ANSI color codes.
    """

    _ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

    def emit(self, record):
        try:
            logger_opt = lg_logger.opt(depth=6, exception=record.exc_info, colors=False)
            clean_message = self._ansi_escape.sub("", record.getMessage())
            logger_opt.log(record.levelname, clean_message)
        except Exception:
            self.handleError(record)


def _setup_logging_interception():
    """
    logger filter
    """
    intercept_handler = InterceptHandler()
    logging.root.handlers = [intercept_handler]
    logging.root.setLevel(LOG_LEVEL)

    logging.basicConfig(
        handlers=[InterceptHandler(level="INFO")], level="INFO", force=True
    )


def register_logger(log_path=None):
    """
    Configure and register logger with loguru for unified log management

    Args:
        log_path: 可选参数，指定日志文件路径。如果为None则使用默认路径
    """
    _setup_logging_interception()

    # 确定日志路径，如果未指定则使用默认路径
    log_file_path = log_path if log_path is not None else DEFAULT_LOG_FILE_PATH
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    file_log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level:^8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    console_log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level:^8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # 移除已有的处理器
    lg_logger.remove()

    # 添加控制台输出
    lg_logger.add(
        sink=sys.stderr,
        level=LOG_LEVEL,
        format=console_log_format,
        colorize=True,
        enqueue=False,
        catch=True,
    )

    # 添加文件输出，支持日志轮换
    lg_logger.add(
        sink=str(log_file_path),
        level="INFO",
        buffering=int(os.getenv("LOGURU_LOGFILE_BUFFERING", "100")),
        rotation="00:00",  # 每天午夜轮换
        serialize=False,
        retention="7 days",  # 保留7天的日志
        format=file_log_format,
        encoding="utf-8"
    )

    return lg_logger
