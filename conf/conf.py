# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : conf.py
Time       ：2025/6/9 14:22
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
import os

import pytz
from dotenv import load_dotenv


PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

load_dotenv()

# ------------------------------history-----------------------------------
# [base]
ENV = os.getenv("ENV", "dev")
TZ = pytz.timezone(os.getenv("TZ", "Asia/Shanghai"))

PORT = int(os.getenv("PORT", 80))
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
GUNICORN_LOG = os.getenv("GUNICORN_LOG", "-")
SECRET_KEY = os.getenv("SECRET_KEY")
GUNICORN_WORKER_NUM = int(os.getenv("GUNICORN_WORKER_NUM", 2))

# [DB]
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_DATABASE = os.getenv("DB_DATABASE", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_URL = os.getenv("LANGFLOW_DATABASE_URL")
VERBOSE = False
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", 300))
POOL_SIZE = int(os.getenv("POOL_SIZE", 100))
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", 100))
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", 30))

# [REDIS]
REDIS_URL = os.getenv('LANGFLOW_REDIS_URL')

# [Celery]
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", 1))
WORKER_MAX_TASKS_PER_CHILD = int(os.getenv("WORKER_MAX_TASKS_PER_CHILD", 10000))
IO_WORKER_CONCURRENCY = int(os.getenv("IO_WORKER_CONCURRENCY", 200))
RAG_PDF_TO_IMAGE_POOL_SIZE = int(os.getenv("RAG_PDF_TO_IMAGE_POOL_SIZE", 8))
RAG_EMBEDDING_POOL_SIZE = int(os.getenv("RAG_EMBEDDING_POOL_SIZE", 8))
RAG_LLM_POOL_SIZE = int(os.getenv("RAG_LLM_POOL_SIZE", 8))
RAG_OTHER_POOL_SIZE = int(os.getenv("RAG_OTHER_POOL_SIZE", 8))
PPT_TO_PDF_NUMS = int(os.getenv("PPT_TO_PDF_NUMS", 3))

# Semaphore 用于限制子进程任务过多，导致 内存泄漏
PDF2IMG_CONVERSION_SEMAPHORE_SIZE = int(
    os.getenv("PDF2IMG_CONVERSION_SEMAPHORE_SIZE", 4)
)
# ppt2pdf/doc2pdf/doc2docx
CONVERT_SEMAPHORE_PPT2PDF_SIZE = int(os.getenv("CONVERT_SEMAPHORE_PPT2PDF_SIZE", 2))
CONVERT_SEMAPHORE_DOC2PDF_SIZE = int(os.getenv("CONVERT_SEMAPHORE_DOC2PDF_SIZE", 2))
CONVERT_SEMAPHORE_DOC2DOCX_SIZE = int(os.getenv("CONVERT_SEMAPHORE_DOC2DOCX_SIZE", 2))
PANDOC_SEMAPHORE_SIZE = int(os.getenv("PANDOC_SEMAPHORE_SIZE", 2))
