from abc import ABC, abstractmethod


class LoggerManagerInterface(ABC):
    @abstractmethod
    def get_logger(self):
        pass

    @abstractmethod
    def info(self, message: str, *args, **kwargs):
        pass

    @abstractmethod
    def error(self, message: str, *args, **kwargs):
        pass

    @abstractmethod
    def debug(self, message: str, *args, **kwargs):
        pass

    @abstractmethod
    def warning(self, message: str, *args, **kwargs):
        pass
