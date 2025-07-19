import logging
import os
from logging.handlers import RotatingFileHandler


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
        try:
            if isinstance(__builtins__, dict):
                tracer_context_global = __builtins__.get("tracer_context")
            else:
                tracer_context_global = getattr(__builtins__, "tracer_context", None)

            if tracer_context_global:
                trace_id = tracer_context_global.get()

                if trace_id == "default_trace_id":
                    try:
                        if isinstance(__builtins__, dict):
                            get_thread_trace_id_func = __builtins__.get(
                                "get_thread_trace_id"
                            )
                        else:
                            get_thread_trace_id_func = getattr(
                                __builtins__, "get_thread_trace_id", None
                            )

                        if get_thread_trace_id_func:
                            thread_trace_id = get_thread_trace_id_func()
                            if thread_trace_id != "default_trace_id":
                                trace_id = thread_trace_id
                    except Exception as e:
                        pass

                record.traceId = trace_id
            else:
                record.traceId = "ERROR_NO_TRACE_CONTEXT"
        except Exception as e:
            record.traceId = "ERROR_TRACE_CONTEXT_FAILED"

        return True


class TenantIDFilter(logging.Filter):
    def filter(self, record):
        try:
            if isinstance(__builtins__, dict):
                tenant_context_global = __builtins__.get("tenant_context")
            else:
                tenant_context_global = getattr(__builtins__, "tenant_context", None)

            if tenant_context_global:
                tenant_id = tenant_context_global.get()

                if tenant_id == "default_tenant":
                    try:
                        if isinstance(__builtins__, dict):
                            get_thread_tenant_id_func = __builtins__.get(
                                "get_thread_tenant_id"
                            )
                        else:
                            get_thread_tenant_id_func = getattr(
                                __builtins__, "get_thread_tenant_id", None
                            )

                        if get_thread_tenant_id_func:
                            thread_tenant_id = get_thread_tenant_id_func()
                            if thread_tenant_id != "default_tenant":
                                tenant_id = thread_tenant_id
                    except Exception as e:
                        pass
        except Exception as e:
            tenant_id = "ERROR_TENANT_FILTER_FAILED"

        if tenant_id == "default_tenant":
            tenant_id = "system"

        record.tenantId = tenant_id
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
    print(
        f"--------setup_logging-------\n: {name}, {log_dir}, {max_bytes}, {backup_count}"
    )
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


def cleanup_logging(name="whisker"):
    """
    Properly cleanup logging handlers to prevent thread cleanup errors

    Args:
        name: logger name to cleanup
    """
    try:
        logger = logging.getLogger(name)

        # Get all handlers before clearing
        handlers = logger.handlers[:]

        # Close all handlers properly
        for handler in handlers:
            try:
                handler.close()
            except Exception as e:
                print(f"Error closing handler {handler}: {e}")

        # Clear all handlers
        logger.handlers.clear()

        # Remove all filters
        logger.filters.clear()

        print(f"Successfully cleaned up logging for: {name}")

    except Exception as e:
        print(f"Error during logging cleanup: {e}")


logger = logging.getLogger("whisker")
