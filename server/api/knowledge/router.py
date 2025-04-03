from typing import List, Union

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
    TextCreate,
    ImageCreate,
    JSONCreate,
    MarkdownCreate,
    PDFCreate,
    GithubRepoCreate,
    QACreate,
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


@router.post("/list", operation_id="get_knowledge_list", response_model_by_alias=False)
async def get_knowledge_list(
    body: PageParams[Knowledge], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Knowledge]]:
    db_engine = PluginManager().dbPlugin
    knowledge_list: PageResponse[Knowledge] = await db_engine.get_knowledge_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=knowledge_list, success=True)


@router.get(
    "/detail", operation_id="get_knowledge_by_id", response_model_by_alias=False
)
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


@router.delete(
    "/delete", operation_id="delete_knowledge", response_model_by_alias=False
)
async def delete_knowledge(
    knowledge_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[None]:
    """
    Deletes a knowledge entry by its ID.
    """
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
