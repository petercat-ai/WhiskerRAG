from typing import List

from whiskerrag_types.model.knowledge import (Knowledge, KnowledgeCreate,
                                              KnowledgeTypeEnum)
from whiskerrag_types.model.tenant import Tenant
from whiskerrag_utils.loader.github.repo_loader import (GitFileElementType,
                                                        GithubRepoLoader)


async def get_knowledge_list_from_github_repo(
    knowledge_create: KnowledgeCreate,
    tenant: Tenant,
) -> List[Knowledge]:
    repo_url = knowledge_create.source_url
    repo_name = knowledge_create.knowledge_name
    auth_info = knowledge_create.auth_info
    branch_name = None
    # Get the branch name from knowledge.source_url. If it contains tree/xxx, then xxx is the branch name. For example,
    # in https://github.com/petercat-ai/petercat/tree/fix/sqs-executes, the branch name is fix/sqs-executes.
    if "tree/" in repo_url:
        branch_name = repo_url.split("tree/")[1]
    github_loader = GithubRepoLoader(repo_name, branch_name, auth_info)
    file_list: List[GitFileElementType] = github_loader.get_file_list()
    github_repo_list: List[Knowledge] = []
    for file in file_list:
        # only support markdown for now
        if not file.path.endswith(".md"):
            continue
        else:
            knowledge = Knowledge(
                **knowledge_create.model_dump(
                    exclude={
                        "knowledge_type",
                        "knowledge_name",
                        "source_url",
                        "tenant_id",
                        "file_size",
                        "file_sha",
                        "metadata",
                    }
                ),
                knowledge_type=KnowledgeTypeEnum.MARKDOWN,
                knowledge_name=f"{file.repo_name}/{file.path}",
                source_url=file.url,
                tenant_id=tenant.tenant_id,
                file_size=file.size,
                file_sha=file.sha,
                metadata={**knowledge_create.metadata, **file.model_dump()},
            )
            github_repo_list.append(knowledge)
    return github_repo_list
