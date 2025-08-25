from typing import Annotated, List

from fastapi import APIRouter, Body, HTTPException, Path
from whiskerrag_types.model import (
    PageQueryParams,
    PageResponse,
    Tagging,
    TaggingCreate,
    Tenant,
)
from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from whiskerrag_types.interface import DBPluginInterface

router = APIRouter(
    prefix="/api/v1/tagging",
    tags=["tagging"],
    responses={404: {"description": "Not found"}},
)


async def get_db_engine() -> DBPluginInterface:
    db_engine = PluginManager().dbPlugin
    if db_engine is None:
        raise HTTPException(status_code=500, detail="DB plugin is not initialized")
    await db_engine.ensure_initialized()
    return db_engine


@router.post("/list", operation_id="get_tagging_list", response_model_by_alias=False)
async def get_tagging_list(
    body: PageQueryParams[Tagging],
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.TAGGING, [Action.READ])
    ],
) -> ResponseModel[PageResponse[Tagging]]:
    db_engine = await get_db_engine()
    tagging_list = await db_engine.get_tagging_list(tenant.tenant_id, body)
    return ResponseModel(data=tagging_list, success=True)


@router.post(
    "/add_list", operation_id="add_tagging_list", response_model_by_alias=False
)
async def add_tagging_list(
    body: List[TaggingCreate],
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.TAGGING, [Action.CREATE])
    ],
) -> ResponseModel[List[Tagging]]:
    db_engine = await get_db_engine()
    created_tags = await db_engine.add_tagging_list(tenant.tenant_id, body)
    return ResponseModel(data=created_tags, success=True)


@router.delete(
    "/{tagging_id}",
    operation_id="delete_tagging_by_id",
    response_model_by_alias=False,
)
async def delete_tagging_by_id(
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.TAGGING, [Action.DELETE])
    ],
    tagging_id: str = Path(..., description="tagging id"),
) -> ResponseModel[None]:
    db_engine = await get_db_engine()
    deleted = await db_engine.delete_tagging_by_id(tenant.tenant_id, tagging_id)
    if not deleted:
        logger.warning(
            "[delete_tagging_by_id][tagging not exists], tagging_id=%s", tagging_id
        )
        raise HTTPException(status_code=404, detail="tagging not exists")
    return ResponseModel(
        success=True, message=f"Tagging {tagging_id} deleted successfully"
    )
