from typing import List
from dao.base import BaseDAO, get_env_variable

from whiskerrag_types.model import Task


class TaskDao(BaseDAO):
    def __init__(self):
        self.TASK_TABLE_NAME = get_env_variable("TASK_TABLE_NAME", "task")

    def update_task_list(self, task_list: List[Task]) -> None:
        self.client.table(self.TASK_TABLE_NAME).upsert(
            [
                task.model_dump(exclude_unset=True, exclude_none=True)
                for task in task_list
            ],
            on_conflict=["task_id"],
        ).execute()
