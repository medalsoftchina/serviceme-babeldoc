import asyncio
import logging
import logging.handlers
import multiprocessing
import multiprocessing.connection
import multiprocessing.queues
import queue
import threading
import traceback
from collections.abc import AsyncGenerator
from functools import partial
from logging.handlers import QueueHandler
from pathlib import Path

from babeldoc.format.pdf.high_level import async_translate as babeldoc_translate
from babeldoc.format.pdf.translation_config import TranslationConfig as BabelDOCConfig
from babeldoc.format.pdf.translation_config import (
    WatermarkOutputMode as BabelDOCWatermarkMode,
)
from babeldoc.glossary import Glossary
from babeldoc.main import create_progress_handler
from rich.logging import RichHandler

from pdf2zh_next.config.model import SettingsModel
from pdf2zh_next.translator import get_translator
from pdf2zh_next.utils import asynchronize


# Custom exception classes for structured error handling
class TranslationError(Exception):
    """Base class for all translation-related errors."""

    def __reduce__(self):
        """Support for pickling the exception when passing between processes."""
        return self.__class__, (str(self),)


class BabeldocError(TranslationError):
    """Error originating from the babeldoc library."""

    def __init__(self, message, original_error=None):
        super().__init__(message)
        self.original_error = original_error

    def __reduce__(self):
        """Support for pickling the exception when passing between processes."""
        return self.__class__, (str(self), self.original_error)

    def __str__(self):
        if self.original_error:
            return f"{super().__str__()} - Original error: {self.original_error}"
        return super().__str__()


class SubprocessError(TranslationError):
    """Error occurring in the translation subprocess outside of babeldoc."""

    def __init__(self, message, traceback_str=None):
        self.raw_message = message
        super().__init__(message)
        self.traceback_str = traceback_str

    def __reduce__(self):
        """Support for pickling the exception when passing between processes."""
        return (self.__class__, (self.raw_message, self.traceback_str))

    def __str__(self):
        if self.traceback_str:
            return f"{super().__str__()}\nTraceback: {self.traceback_str}"
        return super().__str__()


class IPCError(TranslationError):
    """Error in inter-process communication."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

    def __reduce__(self):
        """Support for pickling the exception when passing between processes."""
        return self.__class__, (str(self), self.details)

    def __str__(self):
        if self.details:
            return f"{super().__str__()} - Details: {self.details}"
        return super().__str__()


class SubprocessCrashError(TranslationError):
    """Error occurring when the subprocess crashes unexpectedly."""

    def __init__(self, message, exit_code=None):
        super().__init__(message)
        self.exit_code = exit_code

    def __reduce__(self):
        """Support for pickling the exception when passing between processes."""
        return self.__class__, (str(self), self.exit_code)

    def __str__(self):
        if self.exit_code is not None:
            return f"{super().__str__()} (exit code: {self.exit_code})"
        return super().__str__()


logger = logging.getLogger(__name__)


def _translate_wrapper(
    settings: SettingsModel,
    file: Path,
    pipe_progress_send: multiprocessing.connection.Connection,
    pipe_cancel_message_recv: multiprocessing.connection.Connection,
    logger_queue: multiprocessing.Queue,
):
    logger = logging.getLogger(__name__)
    cancel_event = threading.Event()
    try:
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("pdfminer").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("peewee").setLevel(logging.WARNING)

        queue_handler = QueueHandler(logger_queue)
        logging.basicConfig(level=logging.INFO, handlers=[queue_handler])

        config = create_babeldoc_config(settings, file)

        def cancel_recv_thread():
            try:
                pipe_cancel_message_recv.recv()
                logger.debug("Cancel signal received in subprocess")
                cancel_event.set()
                config.cancel_translation()
            except Exception as e:
                logger.error(f"Error in cancel_recv_thread: {e}")

        cancel_t = threading.Thread(target=cancel_recv_thread, daemon=True)
        cancel_t.start()

        async def translate_wrapper_async():
            try:
                async for event in babeldoc_translate(config):
                    logger.debug(f"sub process generate event: {event}")
                    if event["type"] == "error":
                        # Convert babeldoc error to structured exception
                        error_msg = str(event.get("error", "Unknown babeldoc error"))
                        error = BabeldocError(
                            message=f"Babeldoc translation error: {error_msg}",
                            original_error=error_msg,
                        )
                        pipe_progress_send.send(error)
                        break
                    # Send normal progress events as before
                    pipe_progress_send.send(event)
                    if event["type"] == "finish":
                        break
            except Exception as e:
                # Capture non-babeldoc errors during translation
                tb_str = traceback.format_exc()
                if not cancel_event.is_set():
                    logger.error(f"Error in translate_wrapper_async: {e}\n{tb_str}")
                error = SubprocessError(
                    message=f"Error during translation process: {e}",
                    traceback_str=tb_str,
                )
                try:
                    pipe_progress_send.send(error)
                except Exception as pipe_err:
                    if not cancel_event.is_set():
                        logger.error(f"Failed to send error through pipe: {pipe_err}")

        # Run the async translation in the subprocess's event loop
        try:
            asyncio.run(translate_wrapper_async())
        except Exception as e:
            # Capture errors that might occur outside the async context
            tb_str = traceback.format_exc()
            if not cancel_event.is_set():
                logger.error(f"Error running async translation: {e}\n{tb_str}")
            error = SubprocessError(
                message=f"Failed to run translation process: {e}", traceback_str=tb_str
            )
            try:
                pipe_progress_send.send(error)
            except Exception as pipe_err:
                if not cancel_event.is_set():
                    logger.error(f"Failed to send error through pipe: {pipe_err}")
    except Exception as e:
        # Capture any errors during setup or initialization
        tb_str = traceback.format_exc()
        logger.error(f"Subprocess initialization error: {e}\n{tb_str}")
        try:
            error = SubprocessError(
                message=f"Translation subprocess initialization error: {e}",
                traceback_str=tb_str,
            )
            pipe_progress_send.send(error)
        except Exception as pipe_err:
            if not cancel_event.is_set():
                logger.error(f"Failed to send error through pipe: {pipe_err}")
    finally:
        logger.debug("sub process send close")
        try:
            pipe_progress_send.send(None)
            pipe_progress_send.close()
            logger.debug("sub process close pipe progress send")
        except Exception as e:
            if not cancel_event.is_set():
                logger.error(f"Error closing progress pipe: {e}")

        try:
            logging.getLogger().removeHandler(queue_handler)
            logging.getLogger().addHandler(RichHandler())
            logger_queue.put(None)
            logger_queue.close()
        except Exception as e:
            if not cancel_event.is_set():
                logger.error(f"Error closing logger queue: {e}")


async def _translate_in_subprocess(
        settings: SettingsModel,
        file: Path,
):
    # 30分钟超时设置（与原逻辑一致）
    cb = asynchronize.AsyncCallback(timeout=30 * 60)

    # 1. 替换 multiprocessing.Pipe/Queue：用线程安全队列替代进程间通信
    progress_queue = queue.Queue()  # 替代 pipe_progress_send/recv：传递进度/错误
    cancel_event = threading.Event()  # 替代 pipe_cancel_message：控制翻译取消
    cancel_flag = False

    # 2. 进度接收线程：从队列获取进度，回调到 AsyncCallback（保留原逻辑）
    def recv_thread():
        while True:
            if cancel_event.is_set():
                break
            try:
                # 用超时队列避免阻塞：1秒超时后重新检查取消信号
                event = progress_queue.get(timeout=1)
                if event is None:  # 翻译结束标记
                    logger.debug("recv none event: translation finished")
                    cb.finished_callback_without_args()
                    break

                # 原逻辑：处理进度/错误事件
                if isinstance(event, TranslationError):
                    logger.error(f"Received translation error: {event}")
                    cb.error_callback(event)
                    break
                elif isinstance(event, dict):
                    cb.step_callback(event)  # 进度回调
                else:
                    logger.warning(f"Unexpected event type: {type(event)}")
                    error = IPCError(f"Unexpected event type: {type(event)}")
                    cb.error_callback(error)
                    break
            except queue.Empty:
                continue  # 超时后继续循环，检查取消信号
            except Exception as e:
                if not cancel_event.is_set():
                    logger.error(f"Error in recv thread: {e}")
                error = IPCError(f"Progress receive error: {e}", details=str(e))
                cb.error_callback(error)
                break

    # 3. 翻译执行线程：直接调用 _translate_wrapper（替代原 multiprocessing.Process）
    # 注意：_translate_wrapper 需改为线程安全（若有全局变量/资源，需加锁）
    def translate_thread():
        try:
            # 直接调用翻译逻辑：将原“子进程执行”改为“线程内直接调用”
            # 原 args 中的 pipe_progress_send 替换为 progress_queue（发送进度）
            # 原 pipe_cancel_message_recv 替换为 cancel_event（监听取消信号）
            _translate_wrapper(
                settings=settings,
                file=file,
                progress_queue=progress_queue,  # 传递进度队列
                cancel_event=cancel_event,  # 传递取消信号
                logger=logger  # 直接传递日志对象，替代 logger_queue
            )
        except TranslationError as e:
            # 翻译错误：发送到进度队列，由 recv_thread 回调
            progress_queue.put(e)
        except Exception as e:
            # 其他异常：包装为 IPCError 并回调
            logger.error(f"Translation thread failed: {e}")
            progress_queue.put(IPCError(f"Translation failed: {e}", details=str(e)))
        finally:
            # 翻译结束：发送 None 标记，触发 recv_thread 退出
            progress_queue.put(None)

    # 4. 启动辅助线程（进度接收 + 翻译执行）
    recv_t = threading.Thread(target=recv_thread, daemon=True)  # 守护线程：随主进程退出
    translate_t = threading.Thread(target=translate_thread, daemon=True)
    recv_t.start()
    translate_t.start()

    try:
        # 5. 原逻辑：异步yield进度事件（与Celery任务回调兼容）
        async for event in cb:
            if cb.has_error():
                break  # 有错误时退出循环，由 AsyncCallback 抛出异常
            yield event.args[0]
    except asyncio.CancelledError:
        # Celery 任务被取消时，触发翻译线程停止
        cancel_flag = True
        cancel_event.set()
        logger.info("Translation cancelled by Celery")
        raise
    except KeyboardInterrupt:
        cancel_flag = True
        cancel_event.set()
        logger.info("KeyboardInterrupt received")
    finally:
        # 6. 资源清理：确保线程退出 + 队列关闭（适配Celery任务回收）
        logger.debug("Cleaning up translation resources")

        # 触发翻译线程取消
        cancel_event.set()

        # 等待翻译线程退出（超时2秒，防止卡住）
        translate_t.join(timeout=2)
        if translate_t.is_alive():
            logger.warning("Translation thread did not exit in time")

        # 等待进度接收线程退出（超时2秒）
        recv_t.join(timeout=2)
        if recv_t.is_alive():
            logger.warning("Progress receive thread did not exit in time")

        # 7. 原逻辑：检查翻译是否异常退出（无错误捕获时主动抛出）
        if not cancel_flag:
            # 检查翻译线程是否崩溃且无错误回调
            if not translate_t.is_alive() and not cb.has_error():
                error = SubprocessCrashError(
                    "Translation finished but no result/error captured",
                    exit_code=0  # 单进程无退出码，用0标记正常结束
                )
                raise error
            # 若有未抛出的错误，主动抛出
            elif cb.has_error():
                raise cb.error

        logger.debug("Translation cleanup completed")


def _get_glossaries(settings: SettingsModel) -> list[Glossary] | None:
    glossaries = []
    if not settings.translation.glossaries:
        return None
    for file in settings.translation.glossaries.split(","):
        glossaries.append(
            Glossary.from_csv(Path(file), target_lang_out=settings.translation.lang_out)
        )
    return glossaries


def create_babeldoc_config(settings: SettingsModel, file: Path) -> BabelDOCConfig:
    if not isinstance(settings, SettingsModel):
        raise ValueError(f"{type(settings)} is not SettingsModel")
    translator = get_translator(settings)
    if translator is None:
        raise ValueError("No translator found")

    # 设置分割策略
    split_strategy = None
    if settings.pdf.max_pages_per_part:
        split_strategy = BabelDOCConfig.create_max_pages_per_part_split_strategy(
            settings.pdf.max_pages_per_part
        )

    # 设置水印模式
    watermark_output_mode_maps = {
        "no_watermark": BabelDOCWatermarkMode.NoWatermark,
        "both": BabelDOCWatermarkMode.Both,
        "watermarked": BabelDOCWatermarkMode.Watermarked,
    }

    watermark_output_mode = settings.pdf.watermark_output_mode

    watermark_mode = watermark_output_mode_maps.get(
        watermark_output_mode, BabelDOCWatermarkMode.Watermarked
    )

    table_model = None
    if settings.pdf.translate_table_text:
        from babeldoc.docvision.table_detection.rapidocr import RapidOCRModel

        table_model = RapidOCRModel()

    babeldoc_config = BabelDOCConfig(
        input_file=file,
        font=None,
        pages=settings.pdf.pages,
        output_dir=settings.translation.output,
        doc_layout_model=None,
        translator=translator,
        debug=settings.basic.debug,
        lang_in=settings.translation.lang_in,
        lang_out=settings.translation.lang_out,
        no_dual=settings.pdf.no_dual,
        no_mono=settings.pdf.no_mono,
        qps=settings.translation.qps,
        # 传递原来缺失的参数
        formular_font_pattern=settings.pdf.formular_font_pattern,
        formular_char_pattern=settings.pdf.formular_char_pattern,
        split_short_lines=settings.pdf.split_short_lines,
        short_line_split_factor=settings.pdf.short_line_split_factor,
        disable_rich_text_translate=settings.pdf.disable_rich_text_translate,
        dual_translate_first=settings.pdf.dual_translate_first,
        enhance_compatibility=settings.pdf.enhance_compatibility,
        use_alternating_pages_dual=settings.pdf.use_alternating_pages_dual,
        watermark_output_mode=watermark_mode,
        min_text_length=settings.translation.min_text_length,
        report_interval=settings.report_interval,
        skip_clean=settings.pdf.skip_clean,
        # 添加分割策略
        split_strategy=split_strategy,
        # 添加表格模型，仅在需要翻译表格时
        table_model=table_model,
        skip_scanned_detection=settings.pdf.skip_scanned_detection,
        ocr_workaround=settings.pdf.ocr_workaround,
        custom_system_prompt=settings.translation.custom_system_prompt,
        glossaries=_get_glossaries(settings),
        auto_enable_ocr_workaround=settings.pdf.auto_enable_ocr_workaround,
        pool_max_workers=settings.translation.pool_max_workers,
        auto_extract_glossary=not settings.translation.no_auto_extract_glossary,
        primary_font_family=settings.translation.primary_font_family,
        only_include_translated_page=settings.pdf.only_include_translated_page,
        # BabelDOC v0.5.1 new options
        merge_alternating_line_numbers=not settings.pdf.no_merge_alternating_line_numbers,
        remove_non_formula_lines=not settings.pdf.no_remove_non_formula_lines,
        non_formula_line_iou_threshold=settings.pdf.non_formula_line_iou_threshold,
        figure_table_protection_threshold=settings.pdf.figure_table_protection_threshold,
        skip_formula_offset_calculation=settings.pdf.skip_formula_offset_calculation,
    )
    return babeldoc_config


async def do_translate_async_stream(
    settings: SettingsModel, file: Path | str
) -> AsyncGenerator[dict, None]:
    settings.validate_settings()
    if isinstance(file, str):
        file = Path(file)

    if settings.basic.input_files and len(settings.basic.input_files):
        logger.warning(
            "settings.basic.input_files is for cli & config, "
            "pdf2zh_next.highlevel.do_translate_async_stream will ignore this field "
            "and only translate the file pointed to by the file parameter."
        )

    if not file.exists():
        raise FileNotFoundError(f"file {file} not found")

    # 开始翻译
    translate_func = partial(_translate_in_subprocess, settings, file)

    if settings.basic.debug:
        babeldoc_config = create_babeldoc_config(settings, file)
        logger.debug("debug mode, translate in main process")
        translate_func = partial(babeldoc_translate, translation_config=babeldoc_config)
    else:
        logger.info("translate in subprocess")

    try:
        async for event in translate_func():
            yield event
            if settings.basic.debug:
                logger.debug(event)
            if event["type"] == "finish":
                break
    except TranslationError as e:
        # Log and re-raise structured errors
        logger.error(f"Translation error: {e}")
        if isinstance(e, BabeldocError) and e.original_error:
            logger.error(f"Original babeldoc error: {e.original_error}")
        elif isinstance(e, SubprocessError) and e.traceback_str:
            logger.error(f"Subprocess traceback: {e.traceback_str}")
        # Create an error event to yield to client code
        error_event = {
            "type": "error",
            "error": str(e) if not isinstance(e, SubprocessError) else e.raw_message,
            "error_type": e.__class__.__name__,
            "details": getattr(e, "original_error", "")
            or getattr(e, "traceback_str", "")
            or "",
        }
        yield error_event
        raise  # Re-raise the exception so that the caller can handle it if needed


async def do_translate_file_async(
    settings: SettingsModel, ignore_error: bool = False
) -> int:
    rich_pbar_config = BabelDOCConfig(
        translator=None,
        lang_in=None,
        lang_out=None,
        input_file=None,
        font=None,
        pages=None,
        output_dir=None,
        doc_layout_model=1,
        use_rich_pbar=False,
    )
    progress_context, progress_handler = create_progress_handler(rich_pbar_config)
    input_files = settings.basic.input_files
    assert len(input_files) >= 1, "At least one input file is required"
    settings.basic.input_files = set()

    error_count = 0

    for file in input_files:
        logger.info(f"translate file: {file}")
        # 开始翻译
        with progress_context:
            try:
                async for event in do_translate_async_stream(settings, file):
                    progress_handler(event)
                    if settings.basic.debug:
                        logger.debug(event)
                    if event["type"] == "finish":
                        result = event["translate_result"]
                        logger.info("Translation Result:")
                        logger.info(f"  Original PDF: {result.original_pdf_path}")
                        logger.info(f"  Time Cost: {result.total_seconds:.2f}s")
                        logger.info(f"  Mono PDF: {result.mono_pdf_path or 'None'}")
                        logger.info(f"  Dual PDF: {result.dual_pdf_path or 'None'}")
                        break
                    if event["type"] == "error":
                        error_msg = event.get("error", "Unknown error")
                        error_type = event.get("error_type", "UnknownError")
                        details = event.get("details", "")

                        logger.error(f"Error translating file {file}: {error_msg}")
                        logger.error(f"Error type: {error_type}")
                        if details:
                            logger.error(f"Error details: {details}")

                        error_count += 1
                        if not ignore_error:
                            raise RuntimeError(f"Translation error: {error_msg}")
                        break
            except TranslationError as e:
                # Already logged in do_translate_async_stream
                error_count += 1
                if not ignore_error:
                    raise
            except Exception as e:
                logger.error(f"Error translating file {file}: {e}")
                error_count += 1
                if not ignore_error:
                    raise

    return error_count


def do_translate_file(settings: SettingsModel, ignore_error: bool = False) -> int:
    """
    Translate files synchronously, returning the number of errors encountered.

    Args:
        settings: Translation settings
        ignore_error: If True, continue translating other files when an error occurs

    Returns:
        Number of errors encountered during translation

    Raises:
        TranslationError: If a translation error occurs and ignore_error is False
        Exception: For other errors if ignore_error is False
    """
    try:
        return asyncio.run(do_translate_file_async(settings, ignore_error))
    except KeyboardInterrupt:
        logger.info("Translation interrupted by user (Ctrl+C)")
        return 1  # Return error count = 1 to indicate interruption
    except RuntimeError as e:
        # Handle the case where run() is called from a running event loop
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.get_event_loop()
            try:
                return loop.run_until_complete(
                    do_translate_file_async(settings, ignore_error)
                )
            except KeyboardInterrupt:
                logger.info("Translation interrupted by user (Ctrl+C) in event loop")
                return 1  # Return error count = 1 to indicate interruption
        else:
            raise
