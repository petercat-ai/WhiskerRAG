from typing import Annotated, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel
from whiskerrag_types.model import (
    PageQueryParams,
    PageResponse,
    Tag,
    TagCreate,
    Tenant,
)

from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from whiskerrag_types.interface import DBPluginInterface

router = APIRouter(
    prefix="/api/v1/tag", tags=["tag"], responses={404: {"description": "Not found"}}
)


async def get_db_engine() -> DBPluginInterface:
    db_engine = PluginManager().dbPlugin
    if db_engine is None:
        raise HTTPException(status_code=500, detail="DB plugin is not initialized")
    await db_engine.ensure_initialized()
    return db_engine


@router.post(
    "/list",
    operation_id="get_tag_list",
    response_model_by_alias=False,
)
async def get_tag_list(
    body: PageQueryParams[Tag],
    tenant: Annotated[Tenant, get_tenant_with_permissions(Resource.TAG, [Action.READ])],
) -> ResponseModel[PageResponse[Tag]]:
    """
    分页获取标签列表
    """
    db_engine = await get_db_engine()
    tag_list: PageResponse[Tag] = await db_engine.get_tag_list(tenant.tenant_id, body)
    return ResponseModel(data=tag_list, success=True)


@router.post("/add_list", operation_id="add_tag_list", response_model_by_alias=False)
async def add_tag_list(
    body: List[TagCreate],
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.TAG, [Action.CREATE])
    ],
) -> ResponseModel[List[Tag]]:
    """
    批量新增标签
    注意：根据接口定义，DB 插件方法签名为 add_tag_list(tag_list: List[TagCreate])，
    因此此处直接传入 body。若 TagCreate 需要携带 tenant_id，应由模型或插件内部处理。
    """
    db_engine = await get_db_engine()
    created_tags = await db_engine.add_tag_list(tenant.tenant_id, body)
    return ResponseModel(data=created_tags, success=True)


@router.get("/{tag_id}", operation_id="get_tag_by_id", response_model_by_alias=False)
async def get_tag_by_id(
    tenant: Annotated[Tenant, get_tenant_with_permissions(Resource.TAG, [Action.READ])],
    tag_id: str = Path(..., description="tag id"),
) -> ResponseModel[Tag]:
    """
    获取标签详情
    """
    db_engine = await get_db_engine()
    tag = await db_engine.get_tag_by_id(tenant.tenant_id, tag_id)
    if not tag:
        logger.warning("[get_tag_by_id][tag not exists], tag_id=%s", tag_id)
        raise HTTPException(status_code=404, detail="tag not exists")
    return ResponseModel(data=tag, success=True)


@router.delete(
    "/{tag_id}",
    operation_id="delete_tag_by_id",
    response_model_by_alias=False,
)
async def delete_tag_by_id(
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.TAG, [Action.DELETE])
    ],
    tag_id: str = Path(..., description="tag id"),
) -> ResponseModel[None]:
    db_engine = await get_db_engine()
    deleted = await db_engine.delete_tag_by_id(tenant.tenant_id, tag_id)
    if not deleted:
        logger.warning("[delete_tag_by_id][tag not exists], tag_id=%s", tag_id)
        raise HTTPException(status_code=404, detail="tag not exists")
    return ResponseModel(success=True, message=f"Tag {tag_id} deleted successfully")


class TagUpdate(BaseModel):
    tag_id: str
    name: Optional[str] = None
    description: Optional[str] = None


@router.post("/update", operation_id="update_tag", response_model_by_alias=False)
async def update_tag(
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.TAG, [Action.UPDATE])
    ],
    body: TagUpdate = Body(..., description="要更新的标签字段"),
) -> ResponseModel[Tag]:
    db_engine = await get_db_engine()

    if not body.tag_id:
        raise HTTPException(status_code=400, detail="tag_id is required")

    exist = await db_engine.get_tag_by_id(tenant.tenant_id, body.tag_id)
    if not exist:
        logger.error("[update_tag][标签不存在], tag_id=%s", body.tag_id)
        raise HTTPException(status_code=404, detail=f"标签不存在, tag_id={body.tag_id}")

    updated_tag = await db_engine.update_tag_name_description(
        tenant.tenant_id, body.tag_id, body.name, body.description
    )
    return ResponseModel(success=True, data=updated_tag, message="Update tag succeed")
