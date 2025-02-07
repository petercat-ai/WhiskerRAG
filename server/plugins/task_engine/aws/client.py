import asyncio
import json
from typing import List
import boto3
from whiskerrag_types.interface import TaskEnginPluginInterface, DBPluginInterface
from whiskerrag_types.model import (
    Knowledge,
    KnowledgeCreate,
    KnowledgeSourceType,
    Tenant,
    Task,
    TaskStatus,
)

from plugins.task_engine.aws.utils import get_knowledge_list_from_github_repo


class AWSLambdaTaskEnginePlugin(TaskEnginPluginInterface):
    SQS_QUEUE_URL: str = None
    max_retries: int = 3
    s3_client: boto3.client = None
    sqs_client: boto3.client = None
    db_client: DBPluginInterface = None

    def init(self):
        self.s3_client = boto3.client("s3")
        self.sqs_client = boto3.client("sqs")
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
        asyncio.create_task(self._poll_queue())

    async def _process_message(self, message):
        try:
            self.logger.info(f"Processing message: {message}")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            raise

    async def _poll_queue(self):
        while True:
            try:
                response = self.sqs_client.receive_message(
                    QueueUrl=self.SQS_QUEUE_URL,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,
                    AttributeNames=["All"],
                )

                if "Messages" in response:
                    for message in response["Messages"]:
                        retry_count = 0
                        while retry_count < self.max_retries:
                            try:
                                await self._process_message(message["Body"])
                                self.sqs_client.delete_message(
                                    QueueUrl=self.SQS_QUEUE_URL,
                                    ReceiptHandle=message["ReceiptHandle"],
                                )
                                self.logger.info(
                                    f"Message processed and deleted: {message['MessageId']}"
                                )
                                break

                            except Exception as e:
                                retry_count += 1
                                self.logger.error(f"Attempt {retry_count} failed: {e}")
                                if retry_count == self.max_retries:
                                    self.logger.error(
                                        f"Message processing failed after {self.max_retries} attempts"
                                    )
                                await asyncio.sleep(
                                    1 * retry_count
                                )  # Exponential backoff

            except Exception as e:
                self.logger.error(f"Error polling queue: {e}")
                await asyncio.sleep(10)
