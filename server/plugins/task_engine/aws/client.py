import asyncio
import json
from typing import List
import boto3
from whiskerrag_types.interface import (
    TaskEnginPluginInterface,
)
from whiskerrag_types.model import (
    Knowledge,
    KnowledgeCreate,
    KnowledgeSourceType,
    Tenant,
    Task,
    TaskStatus,
)

from plugins.task_engine.aws.utils import get_knowledge_list_from_github_repo


sqs = boto3.client("sqs")


class AWSLambdaTaskEnginePlugin(TaskEnginPluginInterface):
    SQS_QUEUE_URL: str

    def init(self):
        self.s3_client = boto3.client("s3")
        self.SQS_QUEUE_URL = self.settings.PLUGIN_ENV.get("SQS_QUEUE_URL")
        if self.SQS_QUEUE_URL is None:
            raise Exception(
                "SQS_QUEUE_URL is not set. Please set this variable in the .env file located in the plugins folder."
            )

    async def gen_knowledge_list(
        self, user_input: List[KnowledgeCreate], tenant: Tenant
    ) -> List[Task]:
        knowledge_list: List[Knowledge] = []
        for record in user_input:
            if record.source_type == KnowledgeSourceType.GITHUB_REPO:
                repo_knowledge_list = await get_knowledge_list_from_github_repo(
                    record, tenant
                )
                knowledge_list.extend(repo_knowledge_list)
                continue
            knowledge = Knowledge(
                **record.model_dump(),
                tenant_id=tenant.tenant_id,
            )
            knowledge_list.append(knowledge)

        return knowledge_list

    async def init_task_from_knowledge(
        self, knowledge_list: List[Knowledge], tenant: Tenant
    ) -> List[Task]:
        task_list: List[Task] = []
        for knowledge in knowledge_list:
            task = Task(
                status=TaskStatus.PENDING,
                knowledge_id=knowledge.knowledge_id,
                space_id=knowledge.space_id,
                tenant_id=tenant.tenant_id,
            )
            task_list.append(task)
        return task_list

    async def batch_execute_task(
        self, task_list: List[Task], knowledge_list: List[Knowledge]
    ) -> List[Task]:
        batch_size = 5
        knowledge_dict = {
            knowledge.knowledge_id: knowledge for knowledge in knowledge_list
        }
        combined_list = []
        for task in task_list:
            knowledge = knowledge_dict.get(task.knowledge_id)
            if knowledge:
                combined_list.append(
                    {"task": task.model_dump(), "knowledge": knowledge.model_dump()}
                )

        async def process_batch(batch):
            message_body = json.dumps(batch)
            return sqs.send_message_batch(
                QueueUrl=self.SQS_QUEUE_URL,
                Entries=[
                    {"Id": str(i), "MessageBody": message_body}
                    for i in range(len(batch))
                ],
            )

        for i in range(0, len(combined_list), batch_size):
            batch = combined_list[i : i + batch_size]
            await asyncio.sleep(len(combined_list) / batch_size)
            await process_batch(batch)

        return combined_list

    async def execute_task(self, task_id: str) -> List[Task]:
        pass
