from abc import ABC, abstractmethod
from core.log import logger
from core.config import Settings
from typing import List
from plugin_types.model.knowledge import Knowledge


class DBPluginInterface(ABC):
    settings: Settings

    def __init__(self, settings: Settings):
        logger.info("db plugin is initializing ...")
        self.settings = settings
        self.init()
        logger.info("db plugin initialized.")

    # 初始化数据库连接,检查数据表是否存在,不存在则创建
    @abstractmethod
    async def init(self):
        pass

    @abstractmethod
    async def add_knowledge(self, knowledgeList: List[Knowledge]) -> List[Knowledge]:
        """
        将知识导入知识库内，返回知识 ID
        """
        pass

    @abstractmethod
    async def get_knowledge(self, knowledge_id: str) -> Knowledge:
        """
        获取知识库内的知识
        """
        pass

    @abstractmethod
    async def update_knowledge(self, knowledge: Knowledge):
        """
        更新知识库内的知识
        """
        pass

    @abstractmethod
    async def delete_knowledge(self, knowledge_id_list: List[str]):
        """
        删除知识库内知识
        """
        pass

    @abstractmethod
    async def get_tenant_by_id(self, tenant_id: str):
        """
        获取租户信息
        """
        pass
