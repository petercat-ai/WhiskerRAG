from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Body, HTTPException, Path
from whiskerrag_types.model import (
    PageQueryParams,
    PageResponse,
    Space,
    SpaceCreate,
    SpaceResponse,
    Tenant,
)

router = APIRouter(
    prefix="/api/space", tags=["space"], responses={404: {"description": "Not found"}}
)


@router.post(
    "/list",
    operation_id="get_space_list",
    response_model_by_alias=False,
)
async def get_space_list(
    body: PageQueryParams[Space],
    tenant: Tenant = get_tenant_with_permissions(Resource.SPACE, [Action.READ]),
) -> ResponseModel[PageResponse[SpaceResponse]]:
    db_engine = PluginManager().dbPlugin
    space_list: PageResponse[SpaceResponse] = await db_engine.get_space_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=space_list, success=True)


@router.post("/add", operation_id="add_space", response_model_by_alias=False)
async def add_space(
    body: SpaceCreate,
    tenant: Tenant = get_tenant_with_permissions(Resource.SPACE, [Action.CREATE]),
) -> ResponseModel[SpaceResponse]:
    db_engine = PluginManager().dbPlugin
    created_space = await db_engine.save_space(
        Space(**body.model_dump(), tenant_id=tenant.tenant_id)
    )
    return ResponseModel(data=created_space, success=True)


@router.delete(
    "/{space_id}",
    operation_id="delete_space",
    response_model_by_alias=False,
)
async def delete_space(
    space_id: str = Path(..., description="knowledge base id"),
    tenant: Tenant = get_tenant_with_permissions(Resource.SPACE, [Action.DELETE]),
) -> ResponseModel[None]:
    db_engine = PluginManager().dbPlugin
    space = await db_engine.get_space(tenant.tenant_id, space_id)
    if not space:
        logger.error("[delete_space][知识库不存在],space_id={}".format(space_id))
        raise HTTPException(
            status_code=404, detail=f"知识库不存在, space_id={space_id}"
        )
    await db_engine.delete_space(tenant.tenant_id, space_id)
    return ResponseModel(success=True, message=f"Space {space_id} deleted successfully")


@router.put("/{space_id}", operation_id="update_space", response_model_by_alias=False)
async def update_space(
    space_id: str = Path(..., description="知识库唯一标识符"),
    body: SpaceCreate = Body(..., description="更新后的知识库信息"),
    tenant: Tenant = get_tenant_with_permissions(Resource.SPACE, [Action.UPDATE]),
) -> ResponseModel[SpaceResponse]:
    db_engine = PluginManager().dbPlugin
    existing_space = await db_engine.get_space(tenant.tenant_id, space_id)
    if not existing_space:
        logger.error("[update_space][知识库不存在],space_id={}".format(space_id))
        raise HTTPException(
            status_code=404, detail=f"知识库不存在, space_id={space_id}"
        )
    body.space_id = space_id
    updated_space = await db_engine.update_space(
        Space(**body.model_dump(), tenant_id=tenant.tenant_id)
    )
    return ResponseModel(
        data=updated_space, success=True, message="Update knowledge base succeed"
    )


@router.get(
    "/{space_id}", operation_id="get_space_by_id", response_model_by_alias=False
)
async def get_space_by_id(
    space_id: str = Path(..., description="knowledge base id"),
    tenant: Tenant = get_tenant_with_permissions(Resource.SPACE, [Action.READ]),
) -> ResponseModel[SpaceResponse]:
    db_engine = PluginManager().dbPlugin
    space = await db_engine.get_space(tenant.tenant_id, space_id)
    if not space:
        logger.error(
            "[get_space_by_id][knowledge base not exists],space_id={}".format(space_id)
        )
        raise HTTPException(status_code=404, detail="knowledge base not exists")
    return ResponseModel(data=space, success=True)
