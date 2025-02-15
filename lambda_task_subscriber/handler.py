import multiprocessing
from typing import Dict, List
from whiskerrag_types.model import Task, Knowledge, TaskStatus
from whiskerrag_utils import get_register, RegisterTypeEnum
import asyncio
import json

from dao.chunk_dao import ChunkDao
from dao.task_dao import TaskDao
from dao.base import get_env_variable
from typing import List, Tuple
import asyncio
import logging


memory_limit = (
    int(get_env_variable["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"], 250) * 1024 * 1024
)


class TaskPool:
    def __init__(self, max_size: int):
        self.waiting_pool: List[Tuple[Task, Knowledge]] = []
        self.running_tasks: Dict[str, Tuple[Task, Knowledge]] = {}
        self.max_size = max_size
        self.current_running_size = 0

    def start_task(self, task: Task, knowledge: Knowledge) -> None:
        """将任务标记为开始执行"""
        self.running_tasks[task.task_id] = (task, knowledge)
        self.current_running_size += knowledge.file_size
        self.waiting_pool.remove((task, knowledge))

    def finish_task(self, task: Task, knowledge: Knowledge) -> None:
        """将任务标记为已完成"""
        self.running_tasks.pop(task.task_id)
        self.current_running_size -= knowledge.file_size

    def add_to_waiting(self, task: Task, knowledge: Knowledge) -> None:
        """添加任务到等待池"""
        self.waiting_pool.append((task, knowledge))

    def can_execute(self, file_size: int) -> bool:
        """检查是否可以执行新任务"""
        return self.current_running_size + file_size <= self.max_size

    def get_executable_tasks(self) -> List[Tuple[Task, Knowledge]]:
        """获取当前可以执行的任务"""
        executable_tasks = []
        for task, knowledge in self.waiting_pool:
            if self.can_execute(knowledge.file_size):
                executable_tasks.append((task, knowledge))
        return executable_tasks

    def is_empty(self) -> bool:
        """检查是否还有待执行的任务"""
        return len(self.waiting_pool) == 0


class TaskExecutor:

    def __init__(self):
        self._is_running = False
        self.task_dao = TaskDao()
        self.chunk_dao = ChunkDao()
        print(f"max size is {memory_limit * 0.6}")
        self.pool = TaskPool(max_size=memory_limit * 0.6)
        self.logger = logging.getLogger(__name__)
        self.semaphore = asyncio.Semaphore(min(multiprocessing.cpu_count() * 3, 10))

    def add_task(self, task: Task, knowledge: Knowledge) -> None:
        if knowledge.file_size > self.pool.max_size:
            # File too large, mark task as failed
            task.status = TaskStatus.FAILED
            task.error_message = "file_size exceeds maximum limit"
            self.task_dao.update_task_list([task])
            return
        self.pool.add_to_waiting(task, knowledge)

    async def _handle_task(self, task: Task, knowledge: Knowledge):
        async with self.semaphore:
            chunk_list = []
            try:
                self.pool.start_task(task, knowledge)
                task.status = TaskStatus.RUNNING
                self.task_dao.update_task_list([task])

                knowledge_loader = get_register(
                    RegisterTypeEnum.KNOWLEDGE_LOADER, knowledge.source_type
                )
                embedding_model = get_register(
                    RegisterTypeEnum.EMBEDDING, knowledge.embedding_model_name
                )
                documents = await knowledge_loader(knowledge).load()
                chunk_list = await embedding_model().embed_documents(
                    knowledge, documents
                )
                self.logger.info(f"Successfully processed task: {task.task_id}")
                task.status = TaskStatus.SUCCESS

            except Exception as e:
                self.logger.error(f"Error processing task {task.task_id}: {str(e)}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
            finally:
                self.pool.finish_task(task, knowledge)
                if chunk_list and len(chunk_list) > 0:
                    self.chunk_dao.save_chunk_list(chunk_list)
                self.task_dao.update_task_list([task])

    async def run(self):
        if self._is_running:
            return
        self._is_running = True
        while self._is_running:
            if self.pool.is_empty():
                self._is_running = False
            executable_tasks = self.pool.get_executable_tasks()
            if not executable_tasks:
                # Wait for some running tasks to complete and free up space
                await asyncio.sleep(3)
                continue

            await asyncio.gather(
                *[
                    self._handle_task(task, knowledge)
                    for task, knowledge in executable_tasks
                ]
            )


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
            for item in tasks:
                if "task" not in item or "knowledge" not in item:
                    raise ValueError(
                        "Missing 'task' or 'knowledge' in the record body item"
                    )
                task = Task(**item["task"])
                knowledge = Knowledge(**item["knowledge"])
                executor.add_task(task, knowledge)
            await executor.run()
        except Exception as e:
            print(f"Error parsing record: {e}, record: {record}")


def lambda_handler(event, context):
    try:
        if event:
            print(f"Event: {event},type:{type(event)}; Context: {context},")
            asyncio.run(handle_records(event.get("Records", [])))
        else:
            raise Exception("No event data found")
        return {"statusCode": 200, "message": "Success"}
    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "message": f"{e}"}
