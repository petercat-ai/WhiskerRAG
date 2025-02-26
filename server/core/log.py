import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from core.settings import settings
from whiskerrag_types.interface import LoggerManagerInterface


class ColorCodes:
    GREY = "\x1b[38;21m"
    BLUE = "\x1b[38;5;39m"
    YELLOW = "\x1b[38;5;226m"
    RED = "\x1b[38;5;196m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"


class ColoredFormatter(logging.Formatter):
    def __init__(self, format_str: str) -> None:
        super().__init__(format_str)
        self.FORMATS = {
            logging.DEBUG: ColorCodes.GREY + format_str + ColorCodes.RESET,
            logging.INFO: ColorCodes.BLUE + format_str + ColorCodes.RESET,
            logging.WARNING: ColorCodes.YELLOW + format_str + ColorCodes.RESET,
            logging.ERROR: ColorCodes.RED + format_str + ColorCodes.RESET,
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class LoggerManager(LoggerManagerInterface):
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        if settings.IS_IN_Lambda:
            self._logger.setLevel(logging.INFO)
            self._logger = logging.getLogger()
            # In AWS Lambda environment, log files will be automatically uploaded
            return

        # Get the log file path, defaulting to the logs folder in the current directory
        log_dir = os.getenv("LOG_DIR", "./logs")

        os.makedirs(log_dir, exist_ok=True)

        self._logger = logging.getLogger("app_logger")
        self._logger.setLevel(logging.DEBUG)

        log_filename = os.path.join(
            log_dir, f'app_{datetime.now().strftime("%Y-%m-%d")}.log'
        )
        file_handler = TimedRotatingFileHandler(
            filename=log_filename,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )

        console_handler = logging.StreamHandler()

        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        file_formatter = logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S")
        console_formatter = ColoredFormatter(format_str)

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def get_logger(self):
        return self._logger

    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)


logger = LoggerManager()
