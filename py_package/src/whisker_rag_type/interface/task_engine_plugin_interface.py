from abc import ABC, abstractmethod

from .settings_interface import SettingsInterface
from .logger_interface import LoggerManagerInterface
from whisker_rag_type.model import Knowledge


class TaskEnginPluginInterface(ABC):
    settings: SettingsInterface
    logger: LoggerManagerInterface

    def __init__(self, logger: LoggerManagerInterface, settings: SettingsInterface):
        try:
            logger.info("TaskEngine plugin is initializing...")
            self.settings = settings
            self.logger = logger
            self.init()
            logger.info("TaskEngine plugin is initialized")
        except Exception as e:
            logger.error(f"TaskEngine plugin init error: {e}")

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    async def embed_knowledge_list(
        self, user_id: str, knowledge_list: Knowledge
    ) -> dict:
        pass

    @abstractmethod
    async def test(self, **kwargs) -> dict:
        pass
