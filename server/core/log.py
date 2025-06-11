import logging
import os
from logging.handlers import RotatingFileHandler

from contextvars import ContextVar

tracer_context = ContextVar("trace_id", default="default_trace_id")
tenant_context = ContextVar("tenant_id", default="default_tenant_id")


class ColorFormatter(logging.Formatter):
    """
    Custom formatter for colored logging
    """

    COLORS = {
        "DEBUG": "\033[0m",  # default green
        "INFO": "\033[92m",  # green
        "WARNING": "\033[93m",  # yellow
        "ERROR": "\033[91m",  # red
        "CRITICAL": "\033[95m",  # purple
    }
    RESET = "\033[0m"  # reset color

    def format(self, record):
        # get color by level
        color = self.COLORS.get(record.levelname, self.RESET)

        # format time
        asctime = self.formatTime(record, self.datefmt)

        # format colored prefix: time - level - traceId - tenantId
        colored_prefix = f"{color}{asctime} - {record.levelname} - {record.traceId} - {record.tenantId}{self.RESET}"

        # format remaining part (filename and message)
        remaining_part = f" - {record.filename}:{record.lineno} - {record.getMessage()}"

        return colored_prefix + remaining_part


class TraceIDFilter(logging.Filter):
    def filter(self, record):
        record.traceId = tracer_context.get()
        return True


class TenantIDFilter(logging.Filter):
    def filter(self, record):
        record.tenantId = tenant_context.get()
        return True


def setup_logging(
    name="whisker", log_dir="./tracelog", max_bytes=1024 * 1024 * 1024, backup_count=3
):
    """
    setup logging

    Args:
        name: logger name
        log_dir: log directory
        max_bytes: max size of each log file (default 1GB)
        backup_count: number of backup files (default 3)
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)

    os.makedirs(log_dir, exist_ok=True)

    # 使用RotatingFileHandler替代FileHandler，添加文件轮转功能
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

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(traceId)s - %(tenantId)s - %(pathname)s - %(filename)s - %(lineno)d - %(message)s"
    )

    error_handler.setFormatter(formatter)
    info_handler.setFormatter(formatter)
    warn_handler.setFormatter(formatter)

    logger.addHandler(error_handler)
    logger.addHandler(info_handler)
    logger.addHandler(warn_handler)

    if os.getenv("WHISKER_ENV", "dev") == "dev":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        console_formatter = ColorFormatter(
            "%(asctime)s - %(levelname)s - %(traceId)s - %(tenantId)s - %(filename)s:%(lineno)d - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(TraceIDFilter())
        console_handler.addFilter(TenantIDFilter())

        logger.addHandler(console_handler)

    logger.addFilter(TraceIDFilter())
    logger.addFilter(TenantIDFilter())


logger = logging.getLogger("whisker")
