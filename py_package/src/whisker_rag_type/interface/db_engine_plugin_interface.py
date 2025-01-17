from abc import ABC, abstractmethod
from typing import List

from .settings_interface import SettingsInterface
from .logger_interface import LoggerManagerInterface
from whisker_rag_type.model import Knowledge


class DBPluginInterface(ABC):
    settings: SettingsInterface
    logger: LoggerManagerInterface

    def __init__(self, logger: LoggerManagerInterface, settings: SettingsInterface):
        logger.info("DB plugin is initializing...")
        self.settings = settings
        self.logger = logger
        self.init()
        logger.info("DB plugin is initialized")

    @abstractmethod
    async def init(self):
        pass

    @abstractmethod
    async def add_knowledge(self, knowledgeList: List[Knowledge]) -> List[Knowledge]:
        pass

    @abstractmethod
    async def get_knowledge(self, knowledge_id: str) -> Knowledge:
        pass

    @abstractmethod
    async def update_knowledge(self, knowledge: Knowledge):
        pass

    @abstractmethod
    async def delete_knowledge(self, knowledge_id_list: List[str]):
        pass

    # TODO:编辑 chunk; 获取知识库内分页 chunk; 根据 space_id 分页获取知识;根据 space_id 获取任务列表...

    @abstractmethod
    async def get_tenant_by_id(self, tenant_id: str):
        pass
