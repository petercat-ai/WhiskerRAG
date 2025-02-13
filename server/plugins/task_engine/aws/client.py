import asyncio
import json
from typing import List, Optional

import boto3  # type: ignore
from whiskerrag_types.interface import DBPluginInterface, TaskEnginPluginInterface
from whiskerrag_types.model import (
    Knowledge,
    KnowledgeCreate,
    KnowledgeSourceEnum,
    Task,
    TaskStatus,
    Tenant,
)

from plugins.task_engine.aws.sqs_message_processor import SQSMessageProcessor
from plugins.task_engine.aws.utils import get_knowledge_list_from_github_repo


class AWSLambdaTaskEnginePlugin(TaskEnginPluginInterface):
    SQS_QUEUE_URL: Optional[str] = None
    OUTPUT_QUEUE_URL: Optional[str] = None
    max_retries: int = 3
    s3_client: boto3.client = None
    sqs_client: boto3.client = None
    db_client: Optional[DBPluginInterface] = None
    is_running: bool = False

    def init(self):
        self.s3_client = boto3.client("s3")
        self.sqs_client = boto3.client("sqs")
        self.SQS_QUEUE_URL = self.settings.get_env("SQS_QUEUE_URL", "")
        self.OUTPUT_QUEUE_URL = self.settings.get_env("OUTPUT_QUEUE_URL", "")

        missing_vars = []
        if self.SQS_QUEUE_URL is None:
            missing_vars.append("SQS_QUEUE_URL")
        if self.OUTPUT_QUEUE_URL is None:
            missing_vars.append("OUTPUT_QUEUE_URL")
        if missing_vars:
            raise Exception(
                f"Missing environment variables: {', '.join(missing_vars)}. Please set these variables in the .env file located in the plugins folder."
            )

    async def gen_knowledge_list(
        self, user_input: List[KnowledgeCreate], tenant: Tenant
    ) -> List[Knowledge]:
        knowledge_list: List[Knowledge] = []
        for record in user_input:
            if record.source_type == KnowledgeSourceEnum.GITHUB_REPO:
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
            task = Task(  # type: ignore
                status=TaskStatus.PENDING,
                knowledge_id=knowledge.knowledge_id,
                space_id=knowledge.space_id,
                tenant_id=tenant.tenant_id,
            )
            task_list.append(task)
        return task_list

    async def batch_execute_task(
        self, task_list: List[Task], knowledge_list: List[Knowledge]
    ) -> List[dict]:
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
            return self.sqs_client.send_message_batch(
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

    async def on_task_execute(self, db):
        self.db_client = db
        self.is_running = True
        while self.is_running:
            try:
                response = await asyncio.to_thread(
                    self.sqs_client.receive_message,
                    QueueUrl=self.OUTPUT_QUEUE_URL,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                    AttributeNames=["All"],
                )
                processor = SQSMessageProcessor(
                    self.logger,
                    self.db_client,
                    self.sqs_client,
                    self.s3_client,
                    self.OUTPUT_QUEUE_URL,
                    self.max_retries,
                )
                await processor.handle_response(response)
            except Exception as e:
                self.logger.error(f"Error polling queue: {e}")
                await asyncio.sleep(10)

    async def stop_on_task_execute(self):
        self.is_running = False
