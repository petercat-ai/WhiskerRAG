import logging
import os
from logging.handlers import RotatingFileHandler
from whiskerrag_utils import tracing  # 公共 SDK


class ContextVarFilter(logging.Filter):
    """从 ContextVar 获取值注入到 LogRecord"""

    def __init__(self, ctx_var, attr_name):
        super().__init__()
        self.ctx_var = ctx_var
        self.attr_name = attr_name

    def filter(self, record):
        setattr(record, self.attr_name, self.ctx_var.get())
        return True


class CustomFormatter(logging.Formatter):
    """
    日志格式：
    时间 - logger_name - level - [trace_id] - [user_id] - [tenant_id]
    - [request_url] - file_path - filename - line_no - [logType] - messageStr - extJson
    """

    def format(self, record):
        trace_id = getattr(record, "traceId", "unknown_trace_id")
        user_id = getattr(record, "userId", "unknown_user_id")
        tenant_id = getattr(record, "tenantId", "system")
        request_url = getattr(record, "requestUrl", "unknown_url")
        log_type = getattr(record, "logType", "RequestProcess")
        message_str = getattr(record, "messageStr", record.getMessage())
        ext_json = getattr(record, "extJson", "")

        asctime = self.formatTime(record, self.datefmt)
        return (
            f"{asctime} - {record.name} - {record.levelname} - "
            f"{trace_id} - {user_id} - {tenant_id} - "
            f"{request_url} - {record.pathname} - {record.filename} - {record.lineno} - "
            f"[{log_type}] - {message_str} - {ext_json}"
        )


class ColorFormatter(CustomFormatter):
    """彩色日志 Formatter"""

    COLORS = {
        "DEBUG": "\033[37m",  # 灰色
        "INFO": "\033[92m",  # 绿色
        "WARNING": "\033[93m",  # 黄色
        "ERROR": "\033[91m",  # 红色
        "CRITICAL": "\033[95m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


# core/log.py 关键部分


class ColorLevelFormatter(CustomFormatter):
    """只给前缀 时间 - logger_name - level 加颜色"""

    COLORS = {
        "DEBUG": "\033[37m",  # 灰色
        "INFO": "\033[92m",  # 绿色
        "WARNING": "\033[93m",  # 黄色
        "ERROR": "\033[91m",  # 红色
        "CRITICAL": "\033[95m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        # 先调用父类，获取完整格式化字符串
        trace_id = getattr(record, "traceId", "unknown_trace_id")
        user_id = getattr(record, "userId", "unknown_user_id")
        tenant_id = getattr(record, "tenantId", "system")
        request_url = getattr(record, "requestUrl", "unknown_url")
        log_type = getattr(record, "logType", "RequestProcess")
        message_str = getattr(record, "messageStr", record.getMessage())
        ext_json = getattr(record, "extJson", "")

        asctime = self.formatTime(record, self.datefmt)

        # 前缀加颜色
        color = self.COLORS.get(record.levelname, self.RESET)
        prefix_colored = (
            f"{color}{asctime} - {record.name} - {record.levelname}{self.RESET}"
        )

        return (
            f"{prefix_colored} - "
            f"{trace_id} - {user_id} - {tenant_id} - "
            f"{request_url} - {record.pathname} - {record.filename} - {record.lineno} - "
            f"[{log_type}] - {message_str} - {ext_json}"
        )


def setup_logging(
    name="whisker", log_dir="./tracelog", max_bytes=1024 * 1024 * 1024, backup_count=3
):
    logger = logging.getLogger(name)
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)
    os.makedirs(log_dir, exist_ok=True)

    plain_formatter = CustomFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    # 文件 handler 用无色
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"), maxBytes=max_bytes, backupCount=backup_count
    )
    info_handler = RotatingFileHandler(
        os.path.join(log_dir, "info.log"), maxBytes=max_bytes, backupCount=backup_count
    )
    warn_handler = RotatingFileHandler(
        os.path.join(log_dir, "warn.log"), maxBytes=max_bytes, backupCount=backup_count
    )

    error_handler.setLevel(logging.ERROR)
    info_handler.setLevel(logging.INFO)
    warn_handler.setLevel(logging.WARN)

    for h in (error_handler, info_handler, warn_handler):
        h.setFormatter(plain_formatter)
        logger.addHandler(h)

    # 控制台用彩色（只前缀颜色）
    if os.getenv("WHISKER_ENV", "dev") == "dev":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColorLevelFormatter(datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(console_handler)

    # ContextVar Filter
    logger.addFilter(ContextVarFilter(tracing.trace_id_ctx, "traceId"))
    logger.addFilter(ContextVarFilter(tracing.user_id_ctx, "userId"))
    logger.addFilter(ContextVarFilter(tracing.tenant_id_ctx, "tenantId"))


def cleanup_logging(name="whisker"):
    try:
        logger = logging.getLogger(name)
        handlers = logger.handlers[:]
        for handler in handlers:
            try:
                handler.close()
            except Exception as e:
                print(f"Error closing handler {handler}: {e}")
        logger.handlers.clear()
        logger.filters.clear()
        print(f"Successfully cleaned up logging for: {name}")
    except Exception as e:
        print(f"Error during logging cleanup: {e}")


logger = logging.getLogger("whisker")
