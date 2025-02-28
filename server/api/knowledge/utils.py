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
        "source_type": knowledge_create.source_type,
        "knowledge_name": knowledge_create.knowledge_name,
    }
    if knowledge_create.file_sha:
        eq_conditions["file_sha"] = knowledge_create.file_sha
    res: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant_id=tenant.tenant_id,
        page_params=PageParams[Knowledge](
            page=1,
            page_size=10,
            eq_conditions=eq_conditions,
        ),
    )
    return res.total > 0


async def get_repo_all_knowledge(
    tenant: Tenant, request: KnowledgeCreate
) -> List[Knowledge]:
    db_engine = PluginManager().dbPlugin
    page_size = 100
    knowledge_list: List[Knowledge] = []
    res = await db_engine.get_knowledge_list(
        tenant_id=tenant.tenant_id,
        page_params=PageParams[Knowledge](
            page=1,
            page_size=page_size,
            eq_conditions={
                "space_id": request.space_id,
                "source_type": KnowledgeSourceEnum.GITHUB_FILE,
            },
        ),
    )
    total = res.total
    knowledge_list.extend(res.items)
    if total <= 100:
        return knowledge_list
    page_count = total // page_size + 1
    for page in range(2, page_count + 1):
        res = await db_engine.get_knowledge_list(
            tenant_id=tenant.tenant_id,
            page_params=PageParams[Knowledge](
                page=page,
                page_size=page_size,
                eq_conditions={
                    "space_id": request.space_id,
                    "source_type": KnowledgeSourceEnum.GITHUB_FILE,
                },
            ),
        )
        knowledge_list.extend(res.items)
    return knowledge_list


from typing import List, TypedDict, Optional


class DiffResult(TypedDict):
    to_add: List[Knowledge]
    to_delete: List[Knowledge]
    unchanged: List[Knowledge]


def get_diff_knowledge_lists(
    origin_list: List[Knowledge] = None, new_list: List[Knowledge] = None
) -> DiffResult:
    try:
        origin_list = origin_list or []
        new_list = new_list or []
        origin_map = {item.file_sha: item for item in origin_list}
        to_add = []
        unchanged = []
        for new_item in new_list:
            if new_item.file_sha not in origin_map:
                to_add.append(new_item)
            else:
                unchanged.append(new_item)
                del origin_map[new_item.file_sha]
        to_delete = list(origin_map.values())
        return {"to_add": to_add, "to_delete": to_delete, "unchanged": unchanged}
    except Exception as error:
        print(f"error: {error}")
        return {"to_add": [], "to_delete": [], "unchanged": []}


async def gen_knowledge_list(
    user_input: List[KnowledgeCreate], tenant: Tenant
) -> List[Knowledge]:
    knowledge_list: List[Knowledge] = []
    db_engine = PluginManager().dbPlugin
    for record in user_input:
        is_saved = await is_knowledge_saved(record, tenant)
        # ========== GITHUB_REPO FOLDER =======
        if (
            record.source_type == KnowledgeSourceEnum.GITHUB_REPO
            and record.knowledge_type == KnowledgeTypeEnum.FOLDER
        ):
            repo_knowledge = Knowledge(
                **record.model_dump(),
                tenant_id=tenant.tenant_id,
            )
            current_repo_knowledge_list = await get_repo_all_knowledge(tenant, record)
            if is_saved:
                # check diff
                origin_repo_knowledge_list = await get_knowledge_list_from_github_repo(
                    record, tenant, repo_knowledge
                )
                diff_result = get_diff_knowledge_lists(
                    origin_repo_knowledge_list, current_repo_knowledge_list
                )
                await db_engine.delete_knowledge(
                    tenant.tenant_id,
                    [item.knowledge_id for item in diff_result.get("to_delete")],
                )
                knowledge_list.extend(diff_result.get("to_add"))
            else:
                knowledge_list.append(repo_knowledge)
                knowledge_list.extend(current_repo_knowledge_list)
            continue
        # ========= other knowledge =====
        if is_saved:
            print(f"knowledge {record.knowledge_name} is already saved")
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
