from typing import List, Optional

from whiskerrag_types.model import (
    Knowledge,
    KnowledgeCreate,
    KnowledgeSourceEnum,
    KnowledgeTypeEnum,
    Tenant,
    PageParams,
    PageResponse,
)
from whiskerrag_utils.loader.github.repo_loader import (
    GitFileElementType,
    GithubRepoLoader,
)

from core.plugin_manager import PluginManager


async def is_knowledge_saved(knowledge_create: KnowledgeCreate, tenant: Tenant) -> bool:
    db_engine = PluginManager().dbPlugin
    eq_conditions = {
        "space_id": knowledge_create.space_id,
        "source_type": KnowledgeSourceEnum.GITHUB_REPO,
        "knowledge_name": knowledge_create.knowledge_name,
    }
    if knowledge_create.file_sha:
        eq_conditions["file_sha"] = knowledge_create.file_sha
    res: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant_id=tenant.tenant_id,
        page_params=PageParams(
            page=1,
            page_size=10,
            eq_conditions=eq_conditions,
        ),
    )
    return len(res.items) > 0


async def gen_knowledge_list(
    user_input: List[KnowledgeCreate], tenant: Tenant
) -> List[Knowledge]:
    knowledge_list: List[Knowledge] = []
    for record in user_input:
        is_saved = await is_knowledge_saved(record, tenant)
        if is_saved:
            print(f"knowledge {record.knowledge_name} is already saved")
            continue
        if (
            record.source_type == KnowledgeSourceEnum.GITHUB_REPO
            and record.knowledge_type == KnowledgeTypeEnum.FOLDER
        ):
            repo_knowledge = Knowledge(
                **record.model_dump(),
                tenant_id=tenant.tenant_id,
            )
            knowledge_list.append(repo_knowledge)
            repo_knowledge_list = await get_knowledge_list_from_github_repo(
                record, tenant, repo_knowledge
            )
            knowledge_list.extend(repo_knowledge_list)
            continue
        knowledge = Knowledge(
            **record.model_dump(),
            tenant_id=tenant.tenant_id,
        )
        knowledge_list.append(knowledge)
    return knowledge_list


async def get_knowledge_list_from_github_repo(
    knowledge_create: KnowledgeCreate,
    tenant: Tenant,
    parent: Optional[Knowledge] = None,
) -> List[Knowledge]:
    repo_name = knowledge_create.source_config.repo_name
    auth_info = knowledge_create.source_config.auth_info
    branch_name = knowledge_create.source_config.branch
    github_loader = GithubRepoLoader(repo_name, branch_name, auth_info)
    file_list: List[GitFileElementType] = github_loader.get_file_list()
    github_repo_list: List[Knowledge] = []
    for file in file_list:
        if not file.path.endswith((".md", ".mdx")):
            continue
        else:
            knowledge = Knowledge(
                **knowledge_create.model_dump(
                    exclude={
                        "source_type",
                        "knowledge_type",
                        "knowledge_name",
                        "source_config",
                        "tenant_id",
                        "file_size",
                        "file_sha",
                        "metadata",
                        "parent_id",
                        "enabled",
                    }
                ),
                source_type=KnowledgeSourceEnum.GITHUB_FILE,
                knowledge_type=KnowledgeTypeEnum.MARKDOWN,
                knowledge_name=f"{file.repo_name}/{file.path}",
                source_config={
                    **knowledge_create.source_config.model_dump(),
                    "path": file.path,
                },
                tenant_id=tenant.tenant_id,
                file_size=file.size,
                file_sha=file.sha,
                metadata={},
                parent_id=parent.knowledge_id if parent else None,
                enabled=True,
            )
            github_repo_list.append(knowledge)
    return github_repo_list
