import logging
import multiprocessing
from typing import Any, Dict, List
from whiskerrag_types.model import Task, Knowledge, TaskStatus
from whiskerrag_utils import get_register, RegisterTypeEnum
import asyncio
import json

from dao.chunk_dao import ChunkDao
from dao.task_dao import TaskDao
import asyncio

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TaskExecutor:
    def __init__(self):
        self._is_running = False
        self.task_dao = TaskDao()
        self.chunk_dao = ChunkDao()
        self.semaphore = asyncio.Semaphore(min(multiprocessing.cpu_count() * 3, 10))
        self.logger = logging.getLogger(__name__)

    async def handle_task(self, task: Task, knowledge: Knowledge):
        async with self.semaphore:
            chunk_list = []
            try:
                print("start task", task.task_id)
                task.update(status=TaskStatus.RUNNING)
                self.task_dao.update_task_list([task])

                async def process():
                    knowledge_loader = get_register(
                        RegisterTypeEnum.KNOWLEDGE_LOADER, knowledge.source_type
                    )
                    embedding_model = get_register(
                        RegisterTypeEnum.EMBEDDING, knowledge.embedding_model_name
                    )
                    documents = await knowledge_loader(knowledge).load()
                    return await embedding_model().embed_documents(knowledge, documents)

                chunk_list = await asyncio.wait_for(process(), timeout=60)
                self.logger.info(f"Successfully processed task: {task.task_id}")
                task.update(status=TaskStatus.SUCCESS)
            except asyncio.TimeoutError:
                self.logger.error(f"Task {task.task_id} timed out after 60 seconds")
                task.status = TaskStatus.FAILED
                task.error_message = f"Task timed out after 60 seconds, you can try again or reset knowledge split config"
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"Error processing task {task.task_id}: {str(e)}")
                task.update(status=TaskStatus.FAILED, error_message=str(e))
                await asyncio.sleep(10)
            finally:
                print("end task", task.task_id)
            if chunk_list and len(chunk_list) > 0:
                self.chunk_dao.save_chunk_list(chunk_list)
            self.task_dao.update_task_list([task])


_task_executor = TaskExecutor()


def get_task_executor() -> TaskExecutor:
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
    return _task_executor


async def process_single_record(record: Dict[str, Any]) -> tuple[bool, str]:
    try:
        executor = get_task_executor()
        body = record["body"]
        if not body:
            raise ValueError("Record body is missing")

        if isinstance(body, str):
            body = json.loads(body)

        tasks = body if isinstance(body, list) else [body]
        asyncio_task_list = []

        for item in tasks:
            if "task" not in item or "knowledge" not in item:
                raise ValueError(
                    "Missing 'task' or 'knowledge' in the record body item"
                )

            task = Task(**item["task"])
            knowledge = Knowledge(**item["knowledge"])
            asyncio_task_list.append(executor.handle_task(task, knowledge))

        await asyncio.gather(*asyncio_task_list)
        logger.info(f"Successfully processed record {record['messageId']}")
        return True, record["messageId"]

    except Exception as e:
        logger.error(f"Error processing record {record['messageId']}: {str(e)}")
        return False, record["messageId"]


async def handle_records(
    records: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, str]]]:
    failed_records = []

    for record in records:
        success, message_id = await process_single_record(record)
        if not success:
            failed_records.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failed_records}


def lambda_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, List[Dict[str, str]]]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        records = event.get("Records", [])
        logger.info(f"Processing {len(records)} records")

        result = loop.run_until_complete(handle_records(records))

        failed_count = len(result["batchItemFailures"])
        if failed_count > 0:
            logger.warning(f"{failed_count} records failed and will be retried")

        return result

    except Exception as e:
        logger.error(f"Unexpected error in lambda handler: {str(e)}", exc_info=True)
        return {
            "batchItemFailures": [
                {"itemIdentifier": record["messageId"]}
                for record in event.get("Records", [])
            ]
        }
