import asyncio
import json
from typing import List

import boto3
from whiskerrag_types.interface import (
    TaskEnginPluginInterface,
)
from whiskerrag_types.model import Knowledge, ResourceType, Task, TaskStatus
from whiskerrag_utils.github.repo_loader import GithubRepoLoader

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

    async def execute_task(self, task_id: str) -> List[Task]:
        pass

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
                combined_list.append({**task.model_dump(), **knowledge.model_dump()})

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

    async def _get_knowledge_list_from_repo(
        self,
        knowledge: Knowledge,
    ) -> List[Knowledge]:
        repo_url = knowledge.source_url
        repo_name = knowledge.knowledge_name
        auth_info = knowledge.auth_info
        branch_name = None
        if "tree/" in repo_url:
            branch_name = repo_url.split("tree/")[1]
        github_loader = GithubRepoLoader(repo_name, branch_name, auth_info)
        file_list = github_loader.get_file_list()
        github_repo_list: List[Knowledge] = []
        for file in file_list:
            if not file.name.endswith(".md"):
                continue
            github_repo_list.append(
                Knowledge(
                    **knowledge,
                    **file,
                    source_url=file.url,
                    knowledge_type=ResourceType.GITHUB_FILE,
                )
            )
        return github_repo_list
