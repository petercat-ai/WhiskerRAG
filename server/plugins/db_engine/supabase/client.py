from typing import List, Type, TypeVar

from supabase.client import Client, create_client
from whiskerrag_types.interface import DBPluginInterface
from whiskerrag_types.model import Knowledge, Task, Tenant, PageParams, PageResponse

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SupaBasePlugin(DBPluginInterface):
    supabaseClient: Client = None

    def _check_table_exists(self, client: Client, table_name: str) -> bool:
        try:
            response = client.table(table_name).select("*").limit(0).execute()
            if response.data is not None:
                self.logger.info(f"table '{table_name}' connect success")
                return True
            return False
        except Exception as e:
            self.logger.info(f"检查表 {table_name} 出错: {e}")
            return False

    def get_db_client(self):
        return self.supabaseClient

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
            if not self._check_table_exists(supabase, table_name):
                raise Exception(
                    f"Table {table_name} does not exist, please create the table first"
                )

    async def get_paginated_data(
        self,
        table_name: str,
        model_class: Type[T],
        page_params: PageParams,
    ) -> PageResponse[T]:
        """
        General pagination query method

        Args:
            table_name (str): Table name
            model_class (Type[T]): Data model class
            page_params (PageParams): Pagination parameters
            eq_conditions (Dict[str, any], optional): Dictionary of equality conditions. Defaults to None
            search_fields (List[str], optional): List of search fields. Defaults to None

        Returns:
            PageResponse[T]: Pagination response object
        """
        query = self.supabaseClient.table(table_name)

        if page_params.eq_conditions:
            for field, value in page_params.eq_conditions.items():
                query = query.eq(field, value)

        total_count = query.count().execute()
        total = total_count.count if total_count else 0

        if page_params.order_by:
            order_fields = page_params.order_by.split(",")
            for field in order_fields:
                field = field.strip()
                is_desc = page_params.order_direction.lower() == "desc"
                query = query.order(field, desc=is_desc)

        query = query.range(
            page_params.offset, page_params.offset + page_params.limit - 1
        )

        response = await query.execute()
        data = response.data if response else []

        # Convert to a list of model objects
        items = [model_class(**item) for item in data]

        total_pages = (total + page_params.page_size - 1) // page_params.page_size

        return PageResponse[model_class](
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=total_pages,
        )

    async def save_knowledge_list(
        self, knowledge_list: List[Knowledge]
    ) -> List[Knowledge]:
        knowledge_dicts = [
            knowledge.model_dump(exclude_unset=True) for knowledge in knowledge_list
        ]
        response = (
            self.supabaseClient.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .insert(knowledge_dicts)
            .execute()
        )
        return (
            [Knowledge(**knowledge) for knowledge in response.data]
            if response.data
            else []
        )

    async def get_knowledge_list(
        self, space_id: str, page_params: PageParams
    ) -> PageResponse[Knowledge]:
        return await self.get_paginated_data(
            self.settings.KNOWLEDGE_TABLE_NAME,
            Knowledge,
            page_params,
            eq_conditions={
                "space_id": space_id,
            },
        )

    async def get_knowledge(self, knowledge_id: str) -> Knowledge:
        self.supabaseClient.from_("knowledge").select("*").eq(
            "knowledge_id", knowledge_id
        ).execute()

    async def update_knowledge(self, knowledge: Knowledge):
        self.supabaseClient.from_("knowledge").upsert(knowledge).execute()

    async def delete_knowledge(self, knowledge_id_list: List[str]):
        response = (
            self.supabaseClient.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .delete()
            .in_("knowledge_id", knowledge_id_list)
            .execute()
        )
        return response.data

    async def get_tenant_by_id(self, tenant_id: str):
        """
        根据租户 ID 获取租户信息
        """
        pass

    async def delete_knowledge(self, knowledge_id_list: List[str]):
        pass

    async def save_task_list(self, task_list: List[Task]):
        res = (
            self.supabaseClient.table("task")
            .insert([task.model_dump(exclude_unset=True) for task in task_list])
            .execute()
        )
        return [Task(**task) for task in res.data] if res.data else []

    async def validate_tenant_by_sk(self, secret_key: str) -> bool:
        return self.get_tenant_by_sk(secret_key) is not None

    async def get_tenant_by_sk(self, secret_key: str) -> Tenant | None:
        self.logger.info(f"validate tenant: {secret_key}")
        res = (
            self.supabaseClient.table("tenant")
            .select("*")
            .eq("secret_key", secret_key)
            .execute()
        )
        if res.data[0] is None:
            return None
        tenant_data = res.data[0]
        tenant = Tenant(**tenant_data)
        return tenant
