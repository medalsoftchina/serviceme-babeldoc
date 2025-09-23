# !/usr/bin/env python
# -*-coding:utf-8 -*-
"""
File       : &lt;你的文件名&gt;.py
Time       ：2025/9/16 10:31
Author     ：Ricky
Description：
    本模块用于执行文本翻译任务，并在翻译完成后，将结果同步更新到对应的数据库记录中。
    主要流程包括：
        1. 接收待翻译的文本内容及目标语言参数；
        2. 调用翻译服务或模型进行翻译处理；
        3. 将翻译结果写回或更新到指定的数据库表和记录中。
    适用于需要批量文本翻译并保持数据一致性的业务场景。
"""
import asyncio
import json

from app.services.crud import get_by_attachment_id
from pdf2zh_next.high_level import do_translate_file_async

from app.common.engine.pg_session import get_db_session
from loguru import logger
from tasks.celery_app import app
from pdf2zh_next.config.model import SettingsModel
from tasks.utils.util import generate_llm_settings

@app.task(name="translate")
def translate_file(file_id: str, settings_params: dict):
    with get_db_session() as session:
        attachment = get_by_attachment_id(session, file_id)
        attachment.status = 4
        session.commit()
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            # 初始化入参
            llm_parms = generate_llm_settings(settings_params['translate_engine_settings'])
            settings_params['translate_engine_settings'] = llm_parms
            settings = SettingsModel(**settings_params)
            # 运行异步任务并接收返回值
            mono_path = loop.run_until_complete(do_translate_file_async(settings, ignore_error=False))
            # 更新文件状态为翻译成功
            attachment.status = 3
            extra_info = json.loads(attachment.extra_info)
            extra_info['mono_path'] = str(mono_path)
            attachment.extra_info = json.dumps(extra_info, ensure_ascii=False)
            session.commit()
            return True
        except Exception as e:
            err = str(e)
            logger.info(
                f"translate file: {err}"
            )
            logger.exception(e)
            # 更新文件状态为翻译失败
            attachment.status = 6
            attachment.error_message = f"{e}"[:150]
            session.commit()
            return False