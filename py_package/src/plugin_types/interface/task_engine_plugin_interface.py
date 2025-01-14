from abc import ABC, abstractmethod
from plugin_types.model.knowledge import Knowledge
from core.config import Settings
from core.log import logger


class TaskEnginPluginInterface(ABC):
    settings: Settings

    def __init__(self, settings: Settings):
        logger.info("TaskEngine plugin is initializing...")
        self.settings = settings
        self.logger = logger
        self.init()
        logger.info("TaskEngine plugin is initialized")

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    async def embed_knowledge_list(self, knowledge_list: Knowledge) -> dict:
        pass
