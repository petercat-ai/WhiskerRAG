from typing import List, Union

from core.auth import get_tenant
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Depends, HTTPException
from whiskerrag_types.model import (
    GithubRepoCreate,
    ImageCreate,
    JSONCreate,
    Knowledge,
    KnowledgeCreate,
    MarkdownCreate,
    PageParams,
    PageResponse,
    PDFCreate,
    QACreate,
    Tenant,
    TextCreate,
)

from .utils import gen_knowledge_list

router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_tenant)],
)


@router.post("/add", operation_id="add_knowledge", response_model_by_alias=False)
async def add_knowledge(
    body: List[
        Union[
            KnowledgeCreate,
            TextCreate,
            ImageCreate,
            JSONCreate,
            MarkdownCreate,
            PDFCreate,
            GithubRepoCreate,
            QACreate,
        ]
    ],
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[List[Knowledge]]:
    """
    Duplicate file_sha entries are prohibited.
    Any modifications to split_config or embedding model_name parameters must be performed using dedicated API endpoints."
    """
    logger.info("[add_knowledge][start],req={}".format(body))
    try:
        db_engine = PluginManager().dbPlugin
        task_engine = PluginManager().taskPlugin
        knowledge_list = await gen_knowledge_list(body, tenant)
        if not knowledge_list:
            return ResponseModel(success=True, data=[], message="No knowledge to add")
        saved_knowledge = await db_engine.save_knowledge_list(knowledge_list)
        task_list = await task_engine.init_task_from_knowledge(saved_knowledge, tenant)
        saved_task = await db_engine.save_task_list(task_list)
        await task_engine.batch_execute_task(saved_task, saved_knowledge)
        return ResponseModel(success=True, data=saved_knowledge)
    except Exception as e:
        logger.error(f"[add_knowledge][error], req={body}, error={str(e)}")
        raise HTTPException(status_code=500, detail="新增知识失败")


@router.post("/update", operation_id="update_knowledge")
async def update_knowledge(
    knowledge: Knowledge,
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[Knowledge]:
    logger.info("[update_knowledge][start], req=%s", knowledge)
    try:
        db_engine = PluginManager().dbPlugin
        knowledge_db = await db_engine.get_knowledge(
            tenant.tenant_id, knowledge.knowledge_id
        )
        if not knowledge_db:
            logger.warning(
                "[update_knowledge][知识不存在], knowledge_id=%s",
                knowledge.knowledge_id,
            )
            raise HTTPException(
                status_code=404,
                detail=f"知识不存在,knowledge_id={knowledge.knowledge_id}",
            )
        updated_knowledge = await db_engine.update_knowledge(knowledge)
        return ResponseModel(data=updated_knowledge, success=True)
    except Exception as e:
        logger.error("[update_knowledge][error], req=%s, error=%s", knowledge, str(e))
        raise HTTPException(status_code=500, detail="更新知识失败")


@router.post("/list", operation_id="get_knowledge_list")
async def get_knowledge_list(
    body: PageParams[Knowledge], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Knowledge]]:
    logger.info("[get_knowledge_list][start],req={}".format(body))
    try:
        db_engine = PluginManager().dbPlugin
        knowledge_list: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
            tenant.tenant_id, body
        )
        return ResponseModel(data=knowledge_list, success=True)
    except Exception as e:
        logger.error(f"[get_knowledge_list][error], req={body}, error={str(e)}")
        raise HTTPException(status_code=500, detail="获取知识列表失败")


@router.get(
    "/detail", operation_id="get_knowledge_by_id", response_model_by_alias=False
)
async def get_knowledge_by_id(
    knowledge_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[Knowledge]:
    logger.info("[get_knowledge_by_id][start],req={}".format(knowledge_id))
    try:
        db_engine = PluginManager().dbPlugin
        knowledge = await db_engine.get_knowledge(tenant.tenant_id, knowledge_id)
        if not knowledge:
            logger.warning(
                "[get_knowledge_by_id][知识不存在],knowledge_id={}".format(knowledge_id)
            )
            raise HTTPException(
                status_code=404, detail=f"知识不存在, knowledge_id = {knowledge_id}"
            )
        return ResponseModel(data=knowledge, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"[get_knowledge_by_id][error], req={knowledge_id}, error={str(e)}"
        )
        raise HTTPException(status_code=500, detail="获取知识详情失败")


@router.delete(
    "/delete", operation_id="delete_knowledge", response_model_by_alias=False
)
async def delete_knowledge(
    knowledge_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[None]:
    """
    Deletes a knowledge entry by its ID.
    """
    logger.info("[delete_knowledge][start],req={}".format(knowledge_id))
    try:
        db_engine = PluginManager().dbPlugin
        knowledge = await db_engine.get_knowledge(tenant.tenant_id, knowledge_id)
        if not knowledge:
            raise HTTPException(
                status_code=404, detail=f"Knowledge {knowledge_id} not found"
            )
        await db_engine.delete_knowledge(tenant.tenant_id, [knowledge_id])
        return ResponseModel(
            success=True, message=f"Knowledge {knowledge_id} deleted successfully"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[delete_knowledge][error], req={knowledge_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="删除知识失败")
