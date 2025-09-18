# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : pg_session.py
Time       ：2025/6/9 18:13
Author     ：TyroneTian
Email      : zhichao.tian@medalsoft.com
Description：
"""
import asyncio
from contextlib import contextmanager
# from typing import AsyncGenerator
from typing import Callable
from typing import ContextManager

from sqlalchemy import create_engine
# from sqlalchemy.ext.asyncio import async_sessionmaker
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
# from sqlmodel import SQLModel
# from sqlmodel import text

from loguru import logger
from conf.conf import DATABASE_URL
from conf.conf import MAX_OVERFLOW
from conf.conf import POOL_RECYCLE
from conf.conf import POOL_SIZE
from conf.conf import POOL_TIMEOUT
from conf.conf import VERBOSE

# async_engine = create_async_engine(
#     url=f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}",
#     pool_recycle=POOL_RECYCLE,
#     pool_size=POOL_SIZE,
#     max_overflow=MAX_OVERFLOW,
#     pool_timeout=POOL_TIMEOUT,
#     echo=VERBOSE,
# )

sync_engine = create_engine(
    url=DATABASE_URL,
    pool_recycle=POOL_RECYCLE,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    echo=VERBOSE,
)

# 同步 session
session = scoped_session(
    sessionmaker(bind=sync_engine, future=True, autocommit=False, autoflush=False)
)
# # 异步 session
# async_session = async_sessionmaker(
#     bind=async_engine, expire_on_commit=False, class_=AsyncSession
# )


@contextmanager
def get_db_session() -> ContextManager[Session]:
    """上下文管理器方式获取 session，推荐在 Celery 任务中使用"""
    db_session = session()
    try:
        yield db_session
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db_session.close()
        session.remove()


# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with async_session() as db:
#         yield db


# async def pg_init():
#     """
#     init && test
#     :return:
#     """
#     try:
#         for _ in range(3):
#             async with session() as db:
#                 result = await db.execute(text("SELECT version()"))
#             await asyncio.sleep(0.5)
#
#         logger.info(f"Postgres version: {result.scalar()}")
#
#     except Exception as e:
#         logger.error(
#             f"[Postgres] Cannot connect to Postgres, HOST: {DB_HOST}, PORT: {DB_PORT}, USER: {DB_USER}, ERROR: {e}"
#         )
#         # raise Exception(f"[Postgres] Cannot connect to Postgres for Error: {e}")
#     else:
#         logger.info(
#             f"[PG] postgresql server HOST: {DB_HOST}, PORT: {DB_PORT} already connected"
#         )
#
#
# async def init_db():
#     """创建所有数据库表"""
#     async with async_engine.begin() as conn:
#         await conn.run_sync(SQLModel.metadata.create_all)
#
#     logger.info("Database tables created")


def session_remove_wrap(func: Callable):
    def wrap(*args, **kwargs):
        if session.is_active:
            session.remove()

        res = func(*args, **kwargs)
        session.remove()

        return res

    return wrap


if __name__ == "__main__":

    def main():
        asyncio.run(init_db())
