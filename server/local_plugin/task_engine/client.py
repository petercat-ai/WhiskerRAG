from typing import List, Optional

import boto3  # type: ignore
from whiskerrag_types.interface import TaskEnginPluginInterface
from whiskerrag_types.model import (
    Knowledge,
    KnowledgeTypeEnum,
    Task,
    TaskStatus,
    Tenant,
)
from whiskerrag_utils import get_chunks_by_knowledge, init_register


class LocalEnginePlugin(TaskEnginPluginInterface):
    SQS_QUEUE_URL: Optional[str] = None
    max_retries: int = 3
    sqs_client: boto3.client = None
    is_running: bool = False

    async def init(self):
        init_register("local_plugin.task_engine.registry")

    async def init_task_from_knowledge(
        self, knowledge_list: List[Knowledge], tenant: Tenant
    ) -> List[Task]:
        task_list: List[Task] = []
        for knowledge in knowledge_list:
            if knowledge.knowledge_type is KnowledgeTypeEnum.FOLDER:
                continue
            task = Task(
                status=TaskStatus.PENDING,
                knowledge_id=knowledge.knowledge_id,
                space_id=knowledge.space_id,
                tenant_id=tenant.tenant_id,
            )
            task_list.append(task)
        return task_list

    async def process_task(self, task: Task, knowledge: Knowledge) -> Task:
        try:
            task.status = TaskStatus.RUNNING
            await self.db_plugin.update_task_list([task])
            chunk_list = await get_chunks_by_knowledge(knowledge)
            task.status = TaskStatus.SUCCESS
            await self.db_plugin.save_chunk_list(chunk_list)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
        finally:
            await self.db_plugin.update_task_list([task])
        return task

    async def batch_execute_task(
        self, task_list: List[Task], knowledge_list: List[Knowledge]
    ) -> List[Task]:
        knowledge_dict = {
            knowledge.knowledge_id: knowledge for knowledge in knowledge_list
        }
        for task in task_list:
            knowledge = knowledge_dict.get(task.knowledge_id)
            if knowledge:
                task = await self.process_task(task, knowledge)
        return task_list
