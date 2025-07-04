from typing import List

from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from whiskerrag_types.model import (
    Knowledge,
    KnowledgeCreateUnion,
    PageQueryParams,
    PageResponse,
    Tenant,
)
from whiskerrag_utils.registry import RegisterTypeEnum, get_registry_list

from .utils import gen_knowledge_list

router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)


class EnableStatusUpdate(BaseModel):
    knowledge_id: str
    status: bool


@router.post("/add", operation_id="add_knowledge", response_model_by_alias=False)
async def add_knowledge(
    body: List[KnowledgeCreateUnion],
    tenant: Tenant = get_tenant_with_permissions(Resource.KNOWLEDGE, [Action.CREATE]),
) -> ResponseModel[List[Knowledge]]:
    """
    Duplicate file_sha entries are prohibited.
    Any modifications to split_config or embedding model_name parameters must be performed using dedicated API endpoints."
    """
    db_engine = PluginManager().dbPlugin
    task_engine = PluginManager().taskPlugin
    knowledge_list = await gen_knowledge_list(body, tenant)
    if not knowledge_list:
        return ResponseModel(
            success=True,
            data=[],
            message="No knowledge identified. If you really want to add, please check if the filename is duplicated or modify the file_sha.",
        )
    saved_knowledge = await db_engine.save_knowledge_list(knowledge_list)
    task_list = await task_engine.init_task_from_knowledge(saved_knowledge, tenant)
    saved_task = await db_engine.save_task_list(task_list)
    await task_engine.batch_execute_task(saved_task, saved_knowledge)
    return ResponseModel(success=True, data=saved_knowledge)


@router.post("/update", operation_id="update_knowledge", response_model_by_alias=False)
async def update_knowledge(
    knowledge: Knowledge,
    tenant: Tenant = get_tenant_with_permissions(Resource.KNOWLEDGE, [Action.UPDATE]),
) -> ResponseModel[Knowledge]:
    db_engine = PluginManager().dbPlugin
    knowledge_db = await db_engine.get_knowledge(
        tenant.tenant_id, knowledge.knowledge_id
    )
    if not knowledge_db:
        logger.warning(
            "[update_knowledge][knowledge not exist], knowledge_id=%s",
            knowledge.knowledge_id,
        )
        raise HTTPException(
            status_code=404,
            detail=f"knowledge not exist,knowledge_id={knowledge.knowledge_id}",
        )
    updated_knowledge = await db_engine.update_knowledge(knowledge)
    return ResponseModel(data=updated_knowledge, success=True)


@router.post(
    "/update/enabled",
    operation_id="update_knowledge_enable_status",
    response_model_by_alias=False,
)
async def update_knowledge_enable_status(
    body: EnableStatusUpdate,
    tenant: Tenant = get_tenant_with_permissions(Resource.KNOWLEDGE, [Action.UPDATE]),
) -> ResponseModel[None]:
    db_engine = PluginManager().dbPlugin
    await db_engine.update_knowledge_enabled_status(
        tenant.tenant_id, body.knowledge_id, body.status
    )
    return ResponseModel(data=None, success=True)


@router.post("/list", operation_id="get_knowledge_list", response_model_by_alias=False)
async def get_knowledge_list(
    body: PageQueryParams[Knowledge],
    tenant: Tenant = get_tenant_with_permissions(Resource.KNOWLEDGE, [Action.READ]),
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
    knowledge_id: str,
    tenant: Tenant = get_tenant_with_permissions(Resource.KNOWLEDGE, [Action.READ]),
) -> ResponseModel[Knowledge]:
    db_engine = PluginManager().dbPlugin
    knowledge = await db_engine.get_knowledge(tenant.tenant_id, knowledge_id)
    if not knowledge:
        logger.warning(
            "[get_knowledge_by_id][knowledge not exist],knowledge_id={}".format(
                knowledge_id
            )
        )
        raise HTTPException(
            status_code=404,
            detail=f"knowledge not exist, knowledge_id = {knowledge_id}",
        )
    return ResponseModel(data=knowledge, success=True)


@router.delete(
    "/delete", operation_id="delete_knowledge", response_model_by_alias=False
)
async def delete_knowledge(
    knowledge_id: str,
    tenant: Tenant = get_tenant_with_permissions(Resource.KNOWLEDGE, [Action.DELETE]),
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


@router.get(
    "/embedding/models",
    operation_id="get_embedding_models_list",
    response_model_by_alias=False,
)
async def get_embedding_models_list(
    tenant: Tenant = get_tenant_with_permissions(Resource.PUBLIC, []),
):
    try:
        registries = get_registry_list()
        embedding_registry = registries.get(RegisterTypeEnum.EMBEDDING)
        if not embedding_registry:
            raise KeyError("Embedding registry not found")
        keys = [str(key) for key in embedding_registry._dict.keys()]
        return ResponseModel(success=True, data=keys, message="Success")
    except KeyError as e:
        logger.error(f"[get_embedding_models_list][error], error={str(e)}")
        raise HTTPException(status_code=404, detail=f"Registry not found: {str(e)}")
