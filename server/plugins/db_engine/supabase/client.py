from typing import List, Type, TypeVar
import typing

from pydantic import BaseModel
from supabase.client import Client, create_client
from whiskerrag_types.interface import DBPluginInterface
from whiskerrag_types.model import (
    Chunk,
    Knowledge,
    PageParams,
    PageResponse,
    RetrievalByKnowledgeRequest,
    RetrievalBySpaceRequest,
    RetrievalChunk,
    Task,
    Tenant,
)
from whiskerrag_utils import RegisterTypeEnum, get_register

T = TypeVar("T", bound=BaseModel)


class SupaBasePlugin(DBPluginInterface):
    supabase_client: Client

    def _check_table_exists(self, client: Client, table_name: str) -> bool:
        try:
            response = client.table(table_name).select("*").limit(0).execute()
            if response.data is not None:
                self.logger.info(f"table '{table_name}' connect success")
                return True
            return False
        except Exception as e:
            self.logger.info(f"check table {table_name} error: {e}")
            return False

    def get_db_client(self) -> Client:
        return self.supabase_client

    def init(self) -> None:
        SUPABASE_URL = self.settings.get_env("SUPABASE_URL", "")
        SUPABASE_SERVICE_KEY = self.settings.get_env("SUPABASE_SERVICE_KEY", "")
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise Exception("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.supabase_client = supabase
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

    @typing.no_type_check
    async def _get_paginated_data(
        self,
        table_name: str,
        model_class: Type[T],
        page_params: PageParams,
    ) -> PageResponse[T]:
        query = self.supabase_client.table(table_name)
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

        return PageResponse[Type[model_class]](
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
            self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
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
        return await self._get_paginated_data(
            self.settings.KNOWLEDGE_TABLE_NAME,
            Knowledge,
            page_params,
            eq_conditions={
                "space_id": space_id,
            },
        )

    async def get_knowledge(self, knowledge_id: str) -> Knowledge:
        self.supabase_client.from_(self.settings.KNOWLEDGE_TABLE_NAME).select("*").eq(
            "knowledge_id", knowledge_id
        ).execute()

    async def get_chunk_by_knowledge_id(self, knowledge_id: str) -> List[Chunk]:
        pass

    async def update_knowledge(self, knowledge: Knowledge):
        res = (
            self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .upsert(knowledge)
            .execute()
        )
        return [Knowledge(**knowledge) for knowledge in res.data] if res.data else []

    async def delete_knowledge(self, knowledge_id_list: List[str]) -> List[Knowledge]:
        res = (
            self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .delete()
            .in_("knowledge_id", knowledge_id_list)
            .execute()
        )
        return [Knowledge(**knowledge) for knowledge in res.data] if res.data else []

    async def get_tenant_by_id(self, tenant_id: str) -> Tenant | None:
        pass

    async def save_chunk_list(self, chunk_list: List[Chunk]):
        res = (
            self.supabase_client.table(self.settings.CHUNK_TABLE_NAME)
            .insert(
                [
                    chunk.model_dump(exclude_unset=True, exclude_none=True)
                    for chunk in chunk_list
                ]
            )
            .execute()
        )
        return [Chunk(**chunk) for chunk in res.data] if res.data else []

    async def save_task_list(self, task_list: List[Task]):
        res = (
            self.supabase_client.table(self.settings.TASK_TABLE_NAME)
            .insert(
                [
                    task.model_dump(exclude_unset=True, exclude_none=True)
                    for task in task_list
                ]
            )
            .execute()
        )
        return [Task(**task) for task in res.data] if res.data else []

    async def update_task_list(self, task_list: List[Task]) -> List[Task]:
        task_dicts = [
            task.model_dump(exclude_unset=True, exclude_none=True) for task in task_list
        ]
        res = (
            self.supabase_client.table(self.settings.TASK_TABLE_NAME)
            .upsert(task_dicts, on_conflict=["task_id"])
            .execute()
        )
        return [Task(**task) for task in res.data] if res.data else []

    async def validate_tenant_by_sk(self, secret_key: str) -> bool:
        return self.get_tenant_by_sk(secret_key) is not None

    async def get_tenant_by_sk(self, secret_key: str) -> Tenant | None:
        self.logger.info(f"validate tenant: {secret_key}")
        res = (
            self.supabase_client.table("tenant")
            .select("*")
            .eq("secret_key", secret_key)
            .execute()
        )
        if res.data[0] is None:
            return None
        tenant_data = res.data[0]
        tenant = Tenant(**tenant_data)
        return tenant

    async def search_space_chunk_list(
        self,
        params: RetrievalBySpaceRequest,
    ) -> List[RetrievalChunk]:
        embedding_model = get_register(
            RegisterTypeEnum.EMBEDDING, params.embedding_model_name
        )
        query_embedding = await embedding_model().embed_text(params.question)
        res = self.supabase_client.rpc(
            "search_space_list_chunk",
            {
                "metadata_filter": params,
                "query_embedding": query_embedding,
                "query_embedding_model_name": params.embedding_model_name,
                "space_id_list": params.space_id_list,
                "similarity_threshold": params.similarity_threshold,
            },
        ).execute()
        return [RetrievalChunk(**item) for item in res.data] if res.data else []

    async def search_knowledge_chunk_list(
        self,
        params: RetrievalByKnowledgeRequest,
    ) -> List[RetrievalChunk]:
        EmbeddingCls = get_register(
            RegisterTypeEnum.EMBEDDING, params.embedding_model_name
        )
        embedding_instance = EmbeddingCls()
        query_embedding = await embedding_instance.embed_text(params.question)
        res = self.supabase_client.rpc(
            "search_knowledge_list_chunk",
            {
                "metadata_filter": params.metadata_filter,
                "query_embedding": query_embedding,
                "query_embedding_model_name": params.embedding_model_name,
                "knowledge_id_list": params.knowledge_id_list,
                "similarity_threshold": params.similarity_threshold,
            },
        ).execute()
        return [RetrievalChunk(**item) for item in res.data] if res.data else []
