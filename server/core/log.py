import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

from whiskerrag_types.interface import LoggerManagerInterface

from core.settings import settings


class ColorCodes:
    GREY = "\x1b[38;21m"
    BLUE = "\x1b[38;5;39m"
    YELLOW = "\x1b[38;5;226m"
    RED = "\x1b[38;5;196m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"


class ColoredFormatter(logging.Formatter):
    def __init__(self, format_str):
        super().__init__(format_str)
        self.FORMATS = {
            logging.DEBUG: ColorCodes.GREY + format_str + ColorCodes.RESET,
            logging.INFO: ColorCodes.BLUE + format_str + ColorCodes.RESET,
            logging.WARNING: ColorCodes.YELLOW + format_str + ColorCodes.RESET,
            logging.ERROR: ColorCodes.RED + format_str + ColorCodes.RESET,
        }

    def format(self, record):
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
            self._logger = logging.getLogger()
            # In AWS Lambda environment, log files will be automatically uploaded
            return

        # Get the log file path, defaulting to the logs folder in the current directory
        log_dir = os.getenv("LOG_DIR", "./logs")

        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)

        # 创建 logger
        self._logger = logging.getLogger("app_logger")
        self._logger.setLevel(logging.DEBUG)

        # 创建一个按日期轮转的文件处理器
        log_filename = os.path.join(
            log_dir, f'app_{datetime.now().strftime("%Y-%m-%d")}.log'
        )
        file_handler = TimedRotatingFileHandler(
            filename=log_filename,
            when="midnight",  # 在每天午夜切换日志文件
            interval=1,  # 每天切换一次
            backupCount=30,  # 保留最近30天的日志文件
            encoding="utf-8",
        )

        # 控制台处理器（带颜色）
        console_handler = logging.StreamHandler()

        # 设置日志格式
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        file_formatter = logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S")
        console_formatter = ColoredFormatter(format_str)

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # 添加处理器
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
