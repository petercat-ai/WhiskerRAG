import asyncio
from typing import Any, List, Optional

from core.plugin_manager import PluginManager
from whiskerrag_types.model import (
    Knowledge,
    PageQueryParams,
    PageResponse,
    Tenant,
)
from whiskerrag_types.model.knowledge_create import (
    KNOWLEDGE_CREATE_2_KNOWLEDGE_STRATEGY_MAP,
    KnowledgeCreateUnion,
)


async def _is_knowledge_saved(
    knowledge_create: KnowledgeCreateUnion, tenant: Tenant
) -> Optional[Knowledge]:
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
) -> List[Knowledge]:
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
        return [new_knowledge]
    elif saved_knowledge.file_sha != new_knowledge.file_sha:
        await db_engine.delete_knowledge(
            tenant.tenant_id, [saved_knowledge.knowledge_id]
        )
        return [new_knowledge]
    return []


async def gen_knowledge_list(
    user_input: List[KnowledgeCreateUnion], tenant: Tenant
) -> List[Knowledge]:
    if not user_input:
        return []
    db_engine = PluginManager().dbPlugin
    pre_add_knowledge_list: List[Knowledge] = []
    try:
        tasks = [
            _process_single_knowledge(record, tenant, db_engine)
            for record in user_input
        ]
        results = await asyncio.gather(*tasks)
        for knowledge_list in results:
            pre_add_knowledge_list.extend(knowledge_list)
        return pre_add_knowledge_list

    except Exception as e:
        print(f"Error generating knowledge list: {e}")
        raise
