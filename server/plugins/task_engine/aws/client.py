import asyncio
import json
from typing import Any, List, Optional

import boto3  # type: ignore
from whiskerrag_types.interface import DBPluginInterface, TaskEnginPluginInterface
from whiskerrag_types.model import Knowledge, Task, TaskStatus, Tenant


class AWSLambdaTaskEnginePlugin(TaskEnginPluginInterface):
    SQS_QUEUE_URL: Optional[str] = None
    max_retries: int = 3
    s3_client: boto3.client = None
    sqs_client: boto3.client = None
    db_client: Optional[DBPluginInterface] = None
    is_running: bool = False

    def init(self):
        self.s3_client = boto3.client("s3")
        self.sqs_client = boto3.client("sqs")
        self.SQS_QUEUE_URL = self.settings.get_env("SQS_QUEUE_URL", "")

        missing_vars = []
        if self.SQS_QUEUE_URL is None:
            missing_vars.append("SQS_QUEUE_URL")
        if missing_vars:
            raise Exception(
                f"Missing environment variables: {', '.join(missing_vars)}. Please set these variables in the .env file located in the plugins folder."
            )

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

    async def send_combined_list(
        self, combined_list: List[dict], batch_size: int
    ) -> None:
        async def process_batch(batch) -> Any:
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
            res = await process_batch(batch)
            print(res)

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
                    {
                        "task": task.model_dump(),
                        "knowledge": knowledge.model_dump(),
                        "execute_type": "add",
                    }
                )
        print(self.SQS_QUEUE_URL)
        self.logger.debug("-----------", combined_list)
        self.logger.debug(self.SQS_QUEUE_URL)
        asyncio.create_task(self.send_combined_list(combined_list, batch_size))
        return task_list

    async def batch_skip_task(
        self, task_list: List[Task], knowledge_list: List[Knowledge]
    ) -> List[Task]:
        batch_size = 20
        knowledge_dict = {
            knowledge.knowledge_id: knowledge for knowledge in knowledge_list
        }
        combined_list = []
        for task in task_list:
            knowledge = knowledge_dict.get(task.knowledge_id)
            if knowledge:
                combined_list.append(
                    {
                        "task": task.model_dump(),
                        "knowledge": knowledge.model_dump(),
                        "execute_type": "skip",
                    }
                )
        await self.send_combined_list(combined_list, batch_size)
        return task_list
