from typing import List

from core.auth import get_tenant
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Depends, HTTPException
from whiskerrag_types.model import (
    Knowledge,
    KnowledgeCreate,
    PageParams,
    PageResponse,
    Tenant,
)
from core.log import logger

from .utils import gen_knowledge_list


router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_tenant)],
)


@router.post("/add", operation_id="add_knowledge")
async def add_knowledge(
    body: List[KnowledgeCreate], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[List[Knowledge]]:
    db_engine = PluginManager().dbPlugin
    task_engine = PluginManager().taskPlugin
    knowledge_list = await gen_knowledge_list(body, tenant)
    logger.info(f"knowledge_list: {knowledge_list}")
    if not knowledge_list:
        raise HTTPException(status_code=400, detail="knowledge is already exist")
    saved_knowledge = await db_engine.save_knowledge_list(knowledge_list)
    task_list = await task_engine.init_task_from_knowledge(saved_knowledge, tenant)
    saved_task = await db_engine.save_task_list(task_list)
    await task_engine.batch_execute_task(saved_task, saved_knowledge)
    return ResponseModel(success=True, data=saved_knowledge)


@router.post("/list", operation_id="get_knowledge_list")
async def get_knowledge_list(
    body: PageParams[Knowledge], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Knowledge]]:
    db_engine = PluginManager().dbPlugin
    knowledge_list: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=knowledge_list, success=True)


@router.get("/detail", operation_id="get_knowledge_by_id")
async def get_knowledge_by_id(
    knowledge_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[Knowledge]:
    db_engine = PluginManager().dbPlugin
    knowledge: PageResponse[Knowledge] = await db_engine.get_knowledge(
        tenant.tenant_id, knowledge_id
    )
    if not knowledge:
        raise HTTPException(
            status_code=404, detail=f"Knowledge {knowledge_id} not found"
        )
    return ResponseModel(data=knowledge, success=True)
