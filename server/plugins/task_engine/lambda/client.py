from typing import List
import uuid

import boto3
from whisker_rag_type.interface.task_engine_plugin_interface import (
    TaskEnginPluginInterface,
)
from whisker_rag_type.model import Knowledge, ResourceType, Task, TaskStatus
from whisker_rag_util.github.repo_loader import GithubRepoLoader

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

    async def test(self, **kwargs):
        response = sqs.send_message(
            QueueUrl=self.SQS_QUEUE_URL,
            DelaySeconds=10,
            MessageBody=({"message": "hello", "task_id": uuid.uuid4().hex, **kwargs}),
        )
        print(response)

    async def embed_knowledge_list(self, knowledge_list: List[Knowledge]) -> List[Task]:
        task_list: List[Task] = []
        for knowledge in knowledge_list:
            if knowledge.knowledge_type == ResourceType.GITHUB_REPO:
                # 从 knowledge.source_url 中获取分支名,如果带 tree/xxx 的话，xxx 就是分支名。例如
                # https://github.com/petercat-ai/petercat/tree/fix/sqs-executes 分支名就是 fix/sqs-executes
                repo_knowledge_list = self._get_knowledge_list_from_repo(knowledge)
                self.embed_knowledge_list(repo_knowledge_list)
                continue
            else:
                task = Task(
                    task_id=uuid.uuid4().hex,
                    knowledge_id=knowledge.id,
                    status=TaskStatus.PENDING,
                    space_id=knowledge.space_id,
                    tenant_id=knowledge.tenant_id,
                )
                self.logger.debug(f"task is : {task}")
                task_list.append(task)
                sqs.send_message(
                    QueueUrl=self.SQS_QUEUE_URL,
                    DelaySeconds=10,
                    MessageBody=({**task.model_dump(), **knowledge.model_dump()}),
                )
        return task_list

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
            # 仅选择 .md 文件
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
