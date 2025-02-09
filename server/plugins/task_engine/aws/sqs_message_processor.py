import asyncio
import json
from typing import List

from pydantic import BaseModel
from whiskerrag_types.model import Task, Knowledge, Chunk
from whiskerrag_types.interface import DBPluginInterface


class TaskExecuteResult(BaseModel):
    task: Task
    knowledge: Knowledge
    chunks: List[Chunk]


class SQSMessageProcessor:

    def __init__(
        self,
        logger,
        db_plugin: DBPluginInterface,
        sqs_client,
        s3_client,
        output_queue_url,
        max_retries=3,
    ):
        self.sqs_client = sqs_client
        self.s3_client = s3_client
        self.OUTPUT_QUEUE_URL = output_queue_url
        self.max_retries = max_retries
        self.logger = logger
        self.db_plugin = db_plugin

    def _load_messages_from_s3(self, messages) -> List[TaskExecuteResult]:
        result: List[TaskExecuteResult] = []
        for message in messages:
            if message.get("message_type") == "reference":
                response = self.s3_client.get_object(
                    Bucket=message["bucket"], Key=message["key"]
                )
                origin_execute_result_message = json.loads(response["Body"].read())
                result.append(TaskExecuteResult(**origin_execute_result_message))
        return result

    async def _process_task_execute_result_list(
        self, task_execute_result_list: List[TaskExecuteResult]
    ):
        chunk_list = []
        task_list = []
        for task_execute_result in task_execute_result_list:
            chunk_list.extend(task_execute_result.chunks)
            task_list.append(task_execute_result.task)
            try:
                await asyncio.gather(
                    self.db_plugin.save_chunk_list(chunk_list),
                    self.db_plugin.update_task_list(task_list),
                )
            except Exception as e:
                self.logger.error(f"Error saving to database: {e}")
                raise e

    async def handle_response(self, response):
        if "Messages" not in response:
            return
        self.logger.info(f"Received {len(response['Messages'])} messages")
        for message in response["Messages"]:
            retry_count = 0
            while retry_count < self.max_retries:
                try:
                    sqs_message_list = json.loads(message["Body"])
                    execute_result_list = self._load_messages_from_s3(sqs_message_list)
                    await self._process_task_execute_result_list(execute_result_list)
                    await asyncio.to_thread(
                        self.sqs_client.delete_message,
                        QueueUrl=self.OUTPUT_QUEUE_URL,
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
                    await asyncio.sleep(1 * retry_count)  # Exponential backoff
