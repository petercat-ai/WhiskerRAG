from typing import List, Optional, Tuple, TypedDict
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


class DiffResult(TypedDict):
    to_add: List[Knowledge]
    to_delete: List[Knowledge]
    unchanged: List[Knowledge]


async def is_knowledge_saved(knowledge_create: KnowledgeCreate, tenant: Tenant) -> bool:
    db_engine = PluginManager().dbPlugin
    eq_conditions = {
        "space_id": knowledge_create.space_id,
        "source_type": knowledge_create.source_type,
        "knowledge_name": knowledge_create.knowledge_name,
        "knowledge_type": knowledge_create.knowledge_type,
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


async def get_repo_knowledge(repo_name: str, tenant: Tenant) -> Knowledge:
    db_engine = PluginManager().dbPlugin
    res: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant_id=tenant.tenant_id,
        page_params=PageParams[Knowledge](
            page=1,
            page_size=10,
            eq_conditions={
                "space_id": repo_name,
            },
        ),
    )
    return res.items[0]


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


def get_unique_origin_list(
    origin_list: List[Knowledge],
) -> Tuple[List[Knowledge], List[Knowledge]]:
    to_delete = []
    seen_file_shas = set()
    unique_origin_list = []
    for item in origin_list:
        if item.file_sha not in seen_file_shas:
            seen_file_shas.add(item.file_sha)
            unique_origin_list.append(item)
        else:
            to_delete.append(item)
    return to_delete, unique_origin_list


def get_diff_knowledge_by_sha(
    origin_list: List[Knowledge] = None, new_list: List[Knowledge] = None
) -> DiffResult:
    try:
        origin_list = origin_list or []
        new_list = new_list or []

        to_add = []
        unchanged = []
        to_delete = []
        to_delete_origin, unique_origin_list = get_unique_origin_list(origin_list)
        to_delete.extend(to_delete_origin)
        to_delete_new, unique_new_list = get_unique_origin_list(new_list)
        origin_map = {item.file_sha: item for item in unique_origin_list}
        for new_item in unique_new_list:
            if new_item.file_sha not in origin_map:
                to_add.append(new_item)
            else:
                unchanged.append(new_item)
                del origin_map[new_item.file_sha]
        to_delete.extend(list(origin_map.values()))
        return {"to_add": to_add, "to_delete": to_delete, "unchanged": unchanged}
    except Exception as error:
        print(f"error: {error}")
        return {"to_add": [], "to_delete": [], "unchanged": []}


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


async def gen_knowledge_list(
    user_input: List[KnowledgeCreate], tenant: Tenant
) -> List[Knowledge]:
    pre_add_knowledge_list: List[Knowledge] = []
    db_engine = PluginManager().dbPlugin
    for record in user_input:
        is_saved = await is_knowledge_saved(record, tenant)
        # ========== GITHUB_REPO FOLDER =======
        if (
            record.source_type == KnowledgeSourceEnum.GITHUB_REPO
            and record.knowledge_type == KnowledgeTypeEnum.FOLDER
        ):
            repo_knowledge = (
                await get_repo_knowledge(record.space_id, tenant)
                if is_saved
                else Knowledge(
                    **record.model_dump(),
                    tenant_id=tenant.tenant_id,
                )
            )
            origin_repo_knowledge_list = await get_repo_all_knowledge(tenant, record)
            current_repo_knowledge_list = await get_knowledge_list_from_github_repo(
                record, tenant, repo_knowledge
            )
            if is_saved:
                # check diff
                diff_result = get_diff_knowledge_by_sha(
                    origin_repo_knowledge_list, current_repo_knowledge_list
                )
                delete_knowledge_ids = [
                    item.knowledge_id for item in diff_result.get("to_delete")
                ]
                await db_engine.delete_knowledge(tenant.tenant_id, delete_knowledge_ids)
                pre_add_knowledge_list.extend(diff_result.get("to_add"))
            else:
                pre_add_knowledge_list.append(repo_knowledge)
                pre_add_knowledge_list.extend(current_repo_knowledge_list)
            continue
        # ========= other type knowledge =====
        if is_saved:
            print(f"knowledge {record.knowledge_name} is already saved")
            continue
        knowledge = Knowledge(
            **record.model_dump(),
            tenant_id=tenant.tenant_id,
        )
        pre_add_knowledge_list.append(knowledge)
    return pre_add_knowledge_list
