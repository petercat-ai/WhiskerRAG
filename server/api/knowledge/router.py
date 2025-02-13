from typing import List

from fastapi import APIRouter, Depends
from whiskerrag_types.model import (
    KnowledgeCreate,
    Tenant,
    PageParams,
    PageResponse,
    Knowledge,
)

from core.auth import get_tenant, require_auth
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel

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
    try:
        db_engine = PluginManager().dbPlugin
        task_engine = PluginManager().taskPlugin
        knowledge_list = await task_engine.gen_knowledge_list(body, tenant)
        saved_knowledge = await db_engine.save_knowledge_list(knowledge_list)
        task_list = await task_engine.init_task_from_knowledge(saved_knowledge, tenant)
        saved_task = await db_engine.save_task_list(task_list)
        await task_engine.batch_execute_task(saved_task, saved_knowledge)
        return ResponseModel(success=True, data=saved_knowledge)
    except Exception as e:
        logger.error(e)
        return ResponseModel(success=False, message=str(e))


@router.post("/list")
@require_auth()
async def get_knowledge_list(
    body: PageParams, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel:
    db_engine = PluginManager().dbPlugin
    knowledge_list: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=knowledge_list, success=True)
