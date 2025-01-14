import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


class LoggerManager:
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        # 获取日志文件路径，默认为当前目录下的 logs 文件夹
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

        # 控制台处理器（可选）
        console_handler = logging.StreamHandler()

        # 设置日志格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

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


# 创建全局 logger 实例
logger = LoggerManager()
