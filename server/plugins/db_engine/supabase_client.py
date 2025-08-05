import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, List, Optional, TypeVar, Union, Dict

from fastapi import HTTPException, status
from pydantic import BaseModel
from supabase.client import Client, create_client
from whiskerrag_types.interface import DBPluginInterface
from whiskerrag_types.model import (
    APIKey,
    Chunk,
    GlobalRule,
    Knowledge,
    KnowledgeSourceEnum,
    PageQueryParams,
    PageResponse,
    RetrievalByKnowledgeRequest,
    RetrievalBySpaceRequest,
    RetrievalChunk,
    RetrievalRequest,
    Space,
    Task,
    TaskStatus,
    Tenant,
)
from whiskerrag_types.model.page import QueryParams
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

    async def init(self) -> None:
        SUPABASE_URL = self.settings.get_env("SUPABASE_URL", "")
        SUPABASE_SERVICE_KEY = self.settings.get_env("SUPABASE_SERVICE_KEY", "")
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise Exception("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.supabase_client = supabase
        for table_name in [
            self.settings.KNOWLEDGE_TABLE_NAME,
            self.settings.TASK_TABLE_NAME,
            self.settings.API_KEY_TABLE_NAME,
            self.settings.CHUNK_TABLE_NAME,
            self.settings.TENANT_TABLE_NAME,
        ]:
            if not self._check_table_exists(supabase, table_name):
                raise Exception(
                    f"Table {table_name} does not exist, please create the table first"
                )

    async def cleanup(self) -> None:
        pass

    async def _get_paginated_data(
        self,
        tenant_id: str,
        table_name: str,
        model_class: T,
        page_params: PageQueryParams,
    ) -> PageResponse[T]:
        query = self.supabase_client.table(table_name).select("*", count="exact")
        if page_params.eq_conditions:
            for field, value in page_params.eq_conditions.items():
                if field == "tenant_id" and value != tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Tenant {value} is not allowed to access this data.",
                    )
                if isinstance(value, Enum):
                    value = value.value
                if isinstance(value, BaseModel):
                    value = value.model_dump()
                    query.filter(field, "eq", json.dumps(value))
                    continue
                query = query.eq(field, value)

        if page_params.order_by:
            order_fields = page_params.order_by.split(",")
            for field in order_fields:
                field = field.strip()
                is_desc = page_params.order_direction.lower() == "desc"
                query = query.order(field, desc=is_desc)
        query = query.range(
            page_params.offset, page_params.offset + page_params.limit - 1
        )
        response = query.execute()
        data = response.data if response else []
        total = response.count if response else 0

        # Convert to a list of model objects
        items = [model_class(**item) for item in data]

        total_pages = (total + page_params.page_size - 1) // page_params.page_size

        return PageResponse[T](
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
            total_pages=total_pages,
        )

    # =============== knowledge ===============
    async def save_knowledge_list(
        self, knowledge_list: List[Knowledge]
    ) -> List[Knowledge]:
        knowledge_dicts = [knowledge.model_dump() for knowledge in knowledge_list]
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
        self, tenant_id: str, page_params: PageQueryParams[Knowledge]
    ) -> PageResponse[Knowledge]:
        res = await self._get_paginated_data(
            tenant_id, self.settings.KNOWLEDGE_TABLE_NAME, Knowledge, page_params
        )
        for item in res.items:
            if (
                item.source_type == KnowledgeSourceEnum.GITHUB_REPO
                and item.source_config
                and hasattr(item.source_config, "auth_info")
            ):
                item.source_config.auth_info = "***"

        return res

    async def get_knowledge(self, tenant_id: str, knowledge_id: str) -> Knowledge:
        res = (
            self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .select("*")
            .eq("knowledge_id", knowledge_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return Knowledge(**res.data[0]) if res.data else None

    async def update_knowledge(self, knowledge: Knowledge):
        res = (
            self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .upsert(knowledge.model_dump())
            .execute()
        )
        return [Knowledge(**knowledge) for knowledge in res.data] if res.data else []

    async def delete_knowledge(
        self, tenant_id: str, knowledge_id_list: List[str]
    ) -> List[Knowledge]:
        if not knowledge_id_list:
            return []
        # delete task  and delete chunks
        await self.delete_knowledge_task(tenant_id, knowledge_id_list)
        await self.delete_knowledge_chunk(tenant_id, knowledge_id_list)
        res = (
            self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
            .delete()
            .in_("knowledge_id", knowledge_id_list)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return [Knowledge(**knowledge) for knowledge in res.data] if res.data else []

    async def batch_update_knowledge_retrieval_count(
        self, knowledge_id_list: dict[str, int]
    ) -> None:
        try:
            for knowledge_id, retrieval_count in knowledge_id_list.items():
                res = (
                    self.supabase_client.table(self.settings.KNOWLEDGE_TABLE_NAME)
                    .update({"retrieval_count": retrieval_count})
                    .eq("knowledge_id", knowledge_id)
                    .execute()
                )
                if not res.data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Knowledge entry {knowledge_id} was not found.",
                    )
            return None

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update knowledge retrieval counts: {str(e)}",
            )

    async def update_knowledge_enabled_status(
        self, tenant_id: str, knowledge_id: str, enabled: bool
    ) -> None:
        knowledge = await self.get_knowledge(tenant_id, knowledge_id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge entry {knowledge_id} not found.",
            )
        if knowledge.enabled == enabled:
            return
        knowledge.update(enabled=enabled)
        await self.update_knowledge(knowledge)
        await self.update_chunks_enabled_by_knowledge(knowledge_id, enabled)

    # =============== chunk ===============
    async def save_chunk_list(self, chunk_list: List[Chunk]):
        if not chunk_list:
            return []
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

    async def update_chunk_list(self, chunks: List[Chunk]) -> List[Chunk]:
        if not chunks:
            return []
        updates = [
            chunk.model_dump(exclude_unset=True, exclude_none=True) for chunk in chunks
        ]
        res = (
            self.supabase_client.table(self.settings.CHUNK_TABLE_NAME)
            .upsert(updates)
            .execute()
        )

        return [Chunk(**chunk) for chunk in res.data] if res.data else []

    async def update_chunks_enabled_by_knowledge(
        self, knowledge_id: str, enabled: bool
    ) -> List[Chunk]:
        """
        Update the enabled status of all chunks associated with a specific knowledge_id.

        Args:
            knowledge_id: The ID of the knowledge
            enabled: The new enabled status to set

        Returns:
            List[Chunk]: List of updated chunk objects
        """
        # Prepare the update data
        update_data = {"enabled": enabled}

        # Execute the update query
        res = (
            self.supabase_client.table(self.settings.CHUNK_TABLE_NAME)
            .update(update_data)
            .eq("knowledge_id", knowledge_id)
            .execute()
        )

        # Convert the response data to Chunk objects
        return [Chunk(**chunk) for chunk in res.data] if res.data else []

    async def get_chunk_list(
        self, tenant_id: str, page_params: PageQueryParams[Chunk]
    ) -> PageResponse[Chunk]:
        return await self._get_paginated_data(
            tenant_id,
            self.settings.CHUNK_TABLE_NAME,
            Chunk,
            page_params,
        )

    async def get_chunk_by_id(self, tenant_id: str, chunk_id: str) -> Chunk:
        res = (
            self.supabase_client.table(self.settings.CHUNK_TABLE_NAME)
            .select("*")
            .eq("chunk_id", chunk_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return Chunk(**res.data[0]) if res.data else None

    async def delete_knowledge_chunk(
        self, tenant_id: str, knowledge_ids: List[str]
    ) -> List[Chunk] | None:
        res = (
            self.supabase_client.table(self.settings.CHUNK_TABLE_NAME)
            .delete()
            .in_("knowledge_id", knowledge_ids)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return Chunk(**res.data[0]) if res.data else None

    async def delete_chunk_by_id(
        self, tenant_id: str, chunk_id: str, model_name: str
    ) -> Chunk:
        res = (
            self.supabase_client.table(self.settings.CHUNK_TABLE_NAME)
            .delete()
            .eq("chunk_id", chunk_id)
            .eq("tenant_id", tenant_id)
            .eq("embedding_model_name", model_name)
            .execute()
        )
        return Chunk(**res.data[0]) if res.data else None

    async def get_all_chunk(
        self, tenant_id: str, query_params: QueryParams[Chunk]
    ) -> List[Chunk]:
        pass

    # =============== task ===============
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

    async def get_task_list(
        self, tenant_id: str, page_params: PageQueryParams[Task]
    ) -> PageResponse[Task]:
        return await self._get_paginated_data(
            tenant_id,
            self.settings.TASK_TABLE_NAME,
            Task,
            page_params,
        )

    async def get_task_by_id(self, tenant_id: str, task_id: str) -> Task | None:
        res = (
            self.supabase_client.table(self.settings.TASK_TABLE_NAME)
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("task_id", task_id)
            .execute()
        )
        return Task(**res.data[0]) if res.data else None

    async def delete_knowledge_task(
        self, tenant_id: str, knowledge_ids: List[str]
    ) -> List[Task] | None:
        res = (
            self.supabase_client.table(self.settings.TASK_TABLE_NAME)
            .delete()
            .in_("knowledge_id", knowledge_ids)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return Task(**res.data[0]) if res.data else None

    async def delete_task_by_id(self, tenant_id: str, task_id: str) -> Optional[Task]:
        try:
            query = (
                self.supabase_client.table(self.settings.TASK_TABLE_NAME)
                .select("*")
                .eq("tenant_id", tenant_id)
                .eq("task_id", task_id)
            )

            response = await query.execute()
            task_to_delete = response.data[0] if response.data else None

            if task_to_delete:
                delete_query = (
                    self.supabase.table(self.settings.TASK_TABLE_NAME)
                    .delete()
                    .eq("tenant_id", tenant_id)
                    .eq("task_id", task_id)
                )

                await delete_query.execute()
                return Task(**task_to_delete)

            return None

        except Exception as e:
            raise e

    async def task_statistics(
        self, space_id: str, status: TaskStatus
    ) -> Union[dict[TaskStatus, int], int]:
        # TODO: group by status status
        return {
            TaskStatus.SUCCESS: 0,
            TaskStatus.FAILED: 0,
            TaskStatus.CANCELED: 0,
            TaskStatus.RUNNING: 0,
            TaskStatus.PENDING: 0,
        }

    # =============== tenant ===============
    async def save_tenant(self, tenant: Tenant) -> Tenant | None:
        self.logger.info(f"save tenant: {tenant.tenant_name}")
        res = (
            self.supabase_client.table(self.settings.TENANT_TABLE_NAME)
            .insert(tenant.model_dump(exclude_none=True))
            .execute()
        )
        if res.data[0] is None:
            return None
        tenant_data = res.data[0]
        tenant = Tenant(**tenant_data)
        return tenant

    async def get_tenant_by_sk(self, secret_key: str) -> Tenant | None:
        res = (
            self.supabase_client.table(self.settings.TENANT_TABLE_NAME)
            .select("*")
            .eq("secret_key", secret_key)
            .execute()
        )
        return Tenant(**res.data[0]) if res.data else None

    async def update_tenant(self, tenant: Tenant) -> Tenant:
        res = (
            self.supabase_client.table(self.settings.TENANT_TABLE_NAME)
            .upsert(tenant.model_dump(exclude_unset=True, exclude_none=True))
            .execute()
        )
        return Tenant(**res.data[0]) if res.data else None

    async def validate_tenant_name(self, tenant_name: str) -> bool:
        res = (
            self.supabase_client.table(self.settings.TENANT_TABLE_NAME)
            .select("tenant_name")
            .eq("tenant_name", tenant_name)
            .execute()
        )
        return not bool(res.data)

    async def get_tenant_by_id(self, tenant_id: str) -> Union[Tenant, None]:
        res = (
            self.supabase_client.table(self.settings.TENANT_TABLE_NAME)
            .select("*")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return Tenant(**res.data[0]) if res.data else None

    async def get_tenant_list(
        self, page_params: PageQueryParams[Tenant]
    ) -> PageResponse[Tenant]:
        return await self._get_paginated_data(
            None,  # tenant_id is not needed for tenant list
            self.settings.TENANT_TABLE_NAME,
            Tenant,
            page_params,
        )

    async def delete_tenant_by_id(self, tenant_id: str) -> Union[Tenant, None]:
        pass

    # ============== space =================
    # TODO: add space vo for whiskerrag
    async def delete_space(self, tenant_id) -> None:
        pass

    async def save_space(self, space: Space) -> Space:
        pass

    async def update_space(self, space: Space) -> Space:
        pass

    async def get_space_list(
        self, tenant_id: str, page_params: PageQueryParams[Space]
    ) -> PageResponse[Space]:
        pass

    async def get_space(self, tenant_id: str, space_id: str) -> Space:
        pass

    async def delete_space(
        self, tenant_id: str, space_id: str
    ) -> Union[List[Space], None]:
        pass

    # =============== retrieval ===============
    async def search_space_chunk_list(
        self,
        tenant_id: str,
        params: RetrievalBySpaceRequest,
    ) -> List[RetrievalChunk]:
        embedding_model = get_register(
            RegisterTypeEnum.EMBEDDING, params.embedding_model_name
        )
        try:
            query_embedding = await embedding_model().embed_text(params.question, 10)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate query embedding: {str(e)}",
            )
        res = self.supabase_client.rpc(
            "search_space_list_chunk",
            {
                "metadata_filter": params.metadata_filter,
                "query_embedding": query_embedding,
                "query_embedding_model_name": params.embedding_model_name,
                "space_id_list": params.space_id_list,
                "similarity_threshold": params.similarity_threshold,
                "top": params.top,
                "query_tenant_id": tenant_id,
            },
        ).execute()
        return [RetrievalChunk(**item) for item in res.data] if res.data else []

    async def search_knowledge_chunk_list(
        self,
        tenant_id: str,
        params: RetrievalByKnowledgeRequest,
    ) -> List[RetrievalChunk]:
        EmbeddingCls = get_register(
            RegisterTypeEnum.EMBEDDING, params.embedding_model_name
        )
        embedding_instance = EmbeddingCls()
        query_embedding = await embedding_instance.embed_text(params.question, 10)
        res = self.supabase_client.rpc(
            "search_knowledge_list_chunk",
            {
                "metadata_filter": params.metadata_filter,
                "query_tenant_id": tenant_id,
                "query_embedding": query_embedding,
                "query_embedding_model_name": params.embedding_model_name,
                "knowledge_id_list": params.knowledge_id_list,
                "similarity_threshold": params.similarity_threshold,
                "top": params.top,
            },
        ).execute()
        return [RetrievalChunk(**item) for item in res.data] if res.data else []

    async def retrieve(
        self,
        tenant_id: str,
        params: RetrievalRequest,
    ) -> List[RetrievalChunk]:
        pass

    # =================== api-key ===================
    async def get_api_key_by_value(self, key_value: str) -> Union[APIKey, None]:
        res = (
            self.supabase_client.table(self.settings.API_KEY_TABLE_NAME)
            .select("*")
            .eq("key_value", key_value)
            .execute()
        )
        return APIKey(**res.data[0]) if res.data else None

    async def get_api_key_by_id(self, tenant_id, key_id: str) -> Union[APIKey, None]:
        res = (
            self.supabase_client.table(self.settings.API_KEY_TABLE_NAME)
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("key_id", key_id)
            .execute()
        )
        return APIKey(**res.data[0]) if res.data else None

    async def get_tenant_api_keys(
        self, tenant_id: str, page_params: PageQueryParams[APIKey]
    ) -> PageResponse[APIKey]:
        return await self._get_paginated_data(
            tenant_id,
            self.settings.API_KEY_TABLE_NAME,
            APIKey,
            page_params,
        )

    async def save_api_key(self, api_key: APIKey) -> APIKey:
        api_key_dict = api_key.model_dump()
        res = (
            self.supabase_client.table(self.settings.API_KEY_TABLE_NAME)
            .insert(api_key_dict)
            .execute()
        )
        return APIKey(**res.data[0]) if res.data else None

    async def update_api_key(self, api_key: APIKey) -> Union[APIKey, None]:
        api_key_dict = api_key.model_dump()
        res = (
            self.supabase_client.table(self.settings.API_KEY_TABLE_NAME)
            .update(api_key_dict)
            .eq("key_id", api_key.key_id)
            .execute()
        )
        return APIKey(**res.data[0]) if res.data else None

    async def delete_api_key(self, key_id: str) -> bool:
        res = (
            self.supabase_client.table(self.settings.API_KEY_TABLE_NAME)
            .delete()
            .eq("key_id", key_id)
            .execute()
        )
        return bool(res.data)

    async def get_all_expired_api_keys(self, tenant_id: str) -> List[APIKey]:
        current_time = datetime.now(timezone.utc)
        query = (
            self.supabase_client.table(self.settings.API_KEY_TABLE_NAME)
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
            .lt("expires_at", current_time.isoformat())
        )
        res = query.execute()
        items = [APIKey(**item) for item in res.data] if res.data else []
        return items

    # =================== rule ===================
    async def get_tenant_rule(self, tenant_id: str) -> Optional[str]:
        pass

    async def get_space_rule(self, tenant_id: str, space_id: str) -> Optional[str]:
        pass

    # =================== agent ===================
    async def agent_invoke(self, body: Any) -> AsyncIterator[Any]:
        pass

    # ================= webhook
    async def handle_webhook(
        self,
        tenant: Tenant,
        # webhook type, e.g. knowledge, chunk, etc.
        webhook_type: str,
        # webhook source, e.g. github, yuque, slack, etc.
        source: str,
        # knowledge base id
        knowledge_base_id: str,
        # webhook payload
        payload: Any,
    ) -> Optional[str]:
        return None

    # =================== dashboard ===================
    async def get_system_info(self):
        return {
            "space_count": 0,
            "knowledge_count": 0,
            "task_count": 0,
            "tenant_count": 0,
            "retrieval_count": 0,
            "storage_size": "0 B",
        }

    async def get_tenant_log(self, body: Dict[str, Any], tenant_id: str) -> List[Any]:
        return []
