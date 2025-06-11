from typing import List

from dao.base import BaseDAO, get_env_variable
from dao.chunk_dao import ChunkDao
from dao.task_dao import TaskDao
from whiskerrag_types.model import Knowledge


class KnowledgeDao(BaseDAO):

    def __init__(self):
        self.KNOWLEDGE_TABLE_NAME = get_env_variable(
            "KNOWLEDGE_TABLE_NAME", "knowledge"
        )
        self.chunk_dao = ChunkDao()
        self.task_dao = TaskDao()

    async def get_all_knowledge_list(
        self, tenant_id: str, eq_conditions: dict
    ) -> List[Knowledge]:
        return await self._get_all_paginated_data(
            tenant_id, self.KNOWLEDGE_TABLE_NAME, Knowledge, eq_conditions
        )

    async def delete_knowledge(self, tenant_id: str, knowledge_ids: List[str]):
        if not knowledge_ids:
            return []

        # 1. Delete associated chunks
        self.chunk_dao.delete_knowledge_chunks(knowledge_ids)

        # 2. Delete associated tasks
        self.task_dao.delete_knowledge_tasks(tenant_id, knowledge_ids)

        # 3. Delete the knowledge entries themselves
        res = (
            self.client.table(self.KNOWLEDGE_TABLE_NAME)
            .delete()
            .eq("tenant_id", tenant_id)
            .in_("knowledge_id", knowledge_ids)
            .execute()
        )
        return res

    async def add_knowledge_list(
        self, tenant_id: str, knowledge_list: List[Knowledge]
    ) -> List[Knowledge]:
        insert_data = [
            k.model_dump(exclude_unset=True, exclude_none=True) for k in knowledge_list
        ]
        res = self.client.table(self.KNOWLEDGE_TABLE_NAME).insert(insert_data).execute()

        added_knowledge_with_ids = [Knowledge(**item) for item in res.data]
        return added_knowledge_with_ids
