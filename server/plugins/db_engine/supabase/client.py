from typing import List
from core.log import logger

from supabase.client import Client, create_client
from whisker_rag_type.interface.db_engine_plugin_interface import DBPluginInterface
from whisker_rag_type.model.knowledge import Knowledge


def check_table_exists(client: Client, table_name: str) -> bool:
    """
    检查表是否存在
    :param table_name: 表名
    """
    try:
        response = client.table(table_name).select("*").limit(0).execute()
        if response.data is not None:
            logger.info(f"table '{table_name}' connect success")
            return True
        return False
    except Exception as e:
        logger.info(f"检查表 {table_name} 出错: {e}")
        return False


class SupaBasePlugin(DBPluginInterface):
    supabaseClient: Client = None

    def init(self):
        # 初始化数据库连接
        SUPABASE_URL = self.settings.PLUGIN_ENV.get("SUPABASE_URL", "")
        SUPABASE_SERVICE_KEY = self.settings.PLUGIN_ENV.get("SUPABASE_SERVICE_KEY", "")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.supabaseClient = supabase
        # 检查数据表是否存在
        for table_name in [
            self.settings.KNOWLEDGE_TABLE_NAME,
            self.settings.TASK_TABLE_NAME,
            self.settings.ACTION_TABLE_NAME,
            self.settings.TENANT_TABLE_NAME,
            self.settings.TENANT_TABLE_NAME,
        ]:
            if not check_table_exists(supabase, table_name):
                raise Exception(
                    f"Table {table_name} does not exist, please create the table first"
                )

    async def add_knowledge(self, knowledge_list: List[Knowledge]) -> List[Knowledge]:
        knowledge_dicts = [
            knowledge.model_dump(exclude_unset=True) for knowledge in knowledge_list
        ]
        response = (
            self.supabaseClient.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .insert(knowledge_dicts)
            .execute()
        )
        return response.data

    async def get_knowledge(self, knowledge_id: str) -> Knowledge:
        self.supabaseClient.from_("knowledge").select("*").eq(
            "knowledge_id", knowledge_id
        ).execute()

    async def update_knowledge(self, knowledge: Knowledge):
        self.supabaseClient.from_("knowledge").upsert(knowledge).execute()

    async def delete_knowledge(self, knowledge_id_list: List[str]):
        response = (
            self.supabaseClient.table("github_repo_config")
            .delete()
            .in_("knowledge_id", knowledge_id_list)
            .execute()
        )
        return response

    async def get_tenant_by_id(self, tenant_id: str):
        """
        根据租户 ID 获取租户信息
        """
        pass
