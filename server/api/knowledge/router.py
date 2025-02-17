from typing import List

from fastapi import APIRouter, Depends, HTTPException
from whiskerrag_types.model import (
    KnowledgeCreate,
    Tenant,
    PageParams,
    PageResponse,
    Knowledge,
)

from core.auth import get_tenant, require_auth
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from plugins.task_engine.aws.utils import gen_knowledge_list

router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)


@router.post("/add")
@require_auth()
async def add_knowledge(
    body: List[KnowledgeCreate], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel:
    db_engine = PluginManager().dbPlugin
    task_engine = PluginManager().taskPlugin
    knowledge_list = await gen_knowledge_list(body, tenant)
    saved_knowledge = await db_engine.save_knowledge_list(knowledge_list)
    task_list = await task_engine.init_task_from_knowledge(saved_knowledge, tenant)
    saved_task = await db_engine.save_task_list(task_list)
    await task_engine.batch_execute_task(saved_task, saved_knowledge)
    return ResponseModel(success=True, data=saved_knowledge)


@router.post("/list")
@require_auth()
async def get_knowledge_list(
    body: PageParams[Knowledge], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Knowledge]]:
    db_engine = PluginManager().dbPlugin
    knowledge_list: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=knowledge_list, success=True)


@router.get("/detail")
@require_auth()
async def get_knowledge_by_id(
    knowledge_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel:
    db_engine = PluginManager().dbPlugin
    knowledge: PageResponse[Knowledge] = await db_engine.get_knowledge(
        tenant.tenant_id, knowledge_id
    )
    if not knowledge:
        raise HTTPException(
            status_code=404, detail=f"Knowledge {knowledge_id} not found"
        )
    return ResponseModel(data=knowledge, success=True)
