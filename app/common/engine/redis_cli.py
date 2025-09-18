# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : redis.py
Time       :2025/6/10 17:22
Author     :TyroneTian
Email      : zhichao.tian@medalsoft.com
Description:
"""
import asyncio

import redis
import redis.asyncio as async_redis

from app.common.log import logger
from conf.conf import REDIS_CACHE_DB
from conf.conf import REDIS_HOST
from conf.conf import REDIS_PASSWORD  # noqa F401
from conf.conf import REDIS_PORT

# 异步连接池 - 使用 async_redis.ConnectionPool
async_cache_pool = async_redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_CACHE_DB,
    decode_responses=True,
    max_connections=20,
)

# 异步 Redis 客户端
async_redis_cli = async_redis.Redis(connection_pool=async_cache_pool)

# 同步连接池
normal_cache_pool = redis.ConnectionPool(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_CACHE_DB, decode_responses=True
)

# 同步 Redis 客户端
r_cache = redis.StrictRedis(connection_pool=normal_cache_pool)


async def redis_init():
    """
    redis ping init
    """
    try:
        for i in range(3):
            try:
                await async_redis_cli.ping()
                logger.info(f"Redis server: [{REDIS_HOST}:{REDIS_PORT}] connected")
                return True
            except Exception as e:
                if i < 2:
                    logger.warning(
                        f"Redis connection attempt {i+1} failed, retrying..., {str(e)}"
                    )
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"Redis connection failed after 3 attempts: {e}")
                    raise

        return False

    except Exception as e:
        logger.error(
            f"Redis server: [{REDIS_HOST}:{REDIS_PORT}] connection failed: {e}"
        )
        return False
