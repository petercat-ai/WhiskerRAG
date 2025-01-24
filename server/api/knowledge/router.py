from fastapi import APIRouter, Depends
from typing import List

from core.log import logger
from core.plugin_manager import PluginManager
from core.sha_util import calculate_sha256
from model.response import ResponseModel
from whiskerrag_types.model import (
    Tenant,
    KnowledgeCreate,
)

from core.auth import get_tenant, require_auth
from whiskerrag_utils.knowledge import gen_knowledge_list, gen_task_from_knowledge

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
        knowledge_list = await gen_knowledge_list(body, tenant)
        knowledge_save_res = await db_engine.save_knowledge_list(knowledge_list)
        task_list = await gen_task_from_knowledge(knowledge_save_res, tenant)
        task_save_res = await db_engine.save_task_list(task_list)
        await task_engine.batch_execute_task(task_save_res, knowledge_save_res)
        # TODO: 监听任务执行结果，更新知识状态
        return ResponseModel(success=True, data=knowledge_save_res)
    except Exception as e:
        logger.error(e)
        # TODO: add transaction
        return ResponseModel(success=False, message=str(e))
