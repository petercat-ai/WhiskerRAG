import logging
import multiprocessing
from typing import Dict, List
from whiskerrag_types.model import Task, Knowledge, TaskStatus
from whiskerrag_utils import get_register, RegisterTypeEnum
import asyncio
import json

from dao.chunk_dao import ChunkDao
from dao.task_dao import TaskDao
from dao.base import get_env_variable
import asyncio


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


async def handle_records(records):
    executor = get_task_executor()
    for record in records:
        try:
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
            print("done")
        except Exception as e:
            print(f"Error parsing record: {e}, record: {record}")


def lambda_handler(event, context):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(handle_records(event.get("Records", [])))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise Exception("Processing failed")
