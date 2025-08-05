import asyncio
from typing import Any, List, Optional

from whiskerrag_types.model import (Knowledge, PageQueryParams, PageResponse,
                                    Tenant)
from whiskerrag_types.model.knowledge_create import (
    KNOWLEDGE_CREATE_2_KNOWLEDGE_STRATEGY_MAP, KnowledgeCreateUnion)

from core.plugin_manager import PluginManager


async def _is_knowledge_saved(
    knowledge_create: KnowledgeCreateUnion, tenant: Tenant
) -> Optional[Knowledge]:
    """
    Check if the knowledge is saved in the database.
    By default, we only check the knowledge_name, knowledge_type, source_type, and space_id.
    It means that if the knowledge_name, knowledge_type, source_type, and space_id are the same, the knowledge is considered to be the same. If the file_sha is different, the knowledge is considered to be different,should be deleted and re-added.
    """
    db_engine = PluginManager().dbPlugin
    eq_conditions = {
        "space_id": knowledge_create.space_id,
        "knowledge_name": knowledge_create.knowledge_name,
        "knowledge_type": knowledge_create.knowledge_type,
        "source_type": knowledge_create.source_type,
    }
    res: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant_id=tenant.tenant_id,
        page_params=PageQueryParams[Knowledge](
            page=1,
            page_size=10,
            eq_conditions=eq_conditions,
        ),
    )
    return res.items[0] if res.total > 0 else None


async def _process_single_knowledge(
    record: KnowledgeCreateUnion, tenant: Tenant, db_engine: Any
) -> Optional[Knowledge]:
    saved_knowledge = await _is_knowledge_saved(record, tenant)

    for type_cls, func in KNOWLEDGE_CREATE_2_KNOWLEDGE_STRATEGY_MAP.items():
        if isinstance(record, type_cls):
            new_knowledge = func(record, tenant)
            break
    else:
        new_knowledge = Knowledge(
            **record.model_dump(),
            tenant_id=tenant.tenant_id,
        )
    if not saved_knowledge:
        return new_knowledge

    elif saved_knowledge.file_sha != new_knowledge.file_sha:
        # 仅删除当前文件，不删除子文件
        await db_engine.delete_knowledge(
            tenant.tenant_id, [saved_knowledge.knowledge_id]
        )
        # 旧文件与新文件不同，需要删除旧文件，重新添加新文件,并更新knowledge_id,避免指向旧文件的 parent_id 丢失
        new_knowledge.knowledge_id = saved_knowledge.knowledge_id
        return new_knowledge
    return None


async def gen_knowledge_list(
    user_input: List[KnowledgeCreateUnion], tenant: Tenant
) -> List[Knowledge]:
    if not user_input:
        return []
    db_engine = PluginManager().dbPlugin
    pre_add_knowledge_list: List[Knowledge] = []

    # 创建信号量来控制并发数量为4
    semaphore = asyncio.Semaphore(4)

    async def _process_with_semaphore(record: KnowledgeCreateUnion):
        async with semaphore:
            return await _process_single_knowledge(record, tenant, db_engine)

    try:
        tasks = [_process_with_semaphore(record) for record in user_input]
        results = await asyncio.gather(*tasks)
        for knowledge in results:
            if knowledge is not None:
                pre_add_knowledge_list.append(knowledge)
        return pre_add_knowledge_list

    except Exception as e:
        logger.error(f"Error generating knowledge list: {e}")
        raise
