from typing import List
from github import Github

from plugin_types.model.task import Task
from plugin_types.model.knowledge import Knowledge, ResourceType
from plugin_types.interface.task_engine_plugin_interface import TaskEnginPluginInterface
import boto3

sqs = boto3.client("sqs")


class AWSLambdaTaskEnginePlugin(TaskEnginPluginInterface):
    def init(self):
        self.s3_client = boto3.client("s3")

    async def embed_knowledge_list(self, knowledge_list: List[Knowledge]) -> List[Task]:
        # 判断 knowledge_list 中的知识类型，然后分批处理
        # 记录好任务，并写入数据库中。
        # 其中仓库级别的文件需要进行拆分，所以需要额外处理
        task_list: List[Task] = []
        for knowledge in knowledge_list:
            if knowledge.knowledge_type == ResourceType.GITHUB_REPO:
                github_repo_list: List[Knowledge] = []
                # 仓库级别的知识,获取仓库下全部文件
                github_client = None
                if knowledge.auth_info is None:
                    github_client = Github()
                else:
                    github_client = Github(auth=knowledge.auth_info)
                self.embed_knowledge_list(github_repo_list)

                continue
                # 递归调用本方法
            else:
                # 其他类型的知识，直接处理
                pass
        return task_list
