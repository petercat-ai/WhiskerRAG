from typing import List, Optional

from core.auth import Action, Resource, get_tenant_with_permissions
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter
from pydantic import BaseModel
from whiskerrag_types.model import Tenant

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)


class GlobalInfo(BaseModel):
    space_count: Optional[int] = None
    knowledge_count: Optional[int] = None
    task_count: Optional[int] = None
    tenant_count: Optional[int] = None
    retrieval_count: Optional[int] = None
    # system knowledge storage size
    storage_size: Optional[str] = None


class TenantLog(BaseModel):
    content: str


class TenantLogQuery(BaseModel):
    page: int
    page_size: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@router.get(
    "/global_info", operation_id="get_global_info", response_model_by_alias=False
)
async def get_system_global_info() -> ResponseModel[GlobalInfo]:
    db_engine = PluginManager().dbPlugin
    system_info = await db_engine.get_system_info()
    return ResponseModel(
        success=True,
        data=system_info,
        message="Success",
    )


@router.get("/tenant_log", operation_id="get_tenant_log", response_model_by_alias=False)
async def get_tenant_log(
    body: TenantLogQuery,
    tenant: Tenant = get_tenant_with_permissions(Resource.TENANT, [Action.READ]),
) -> ResponseModel[List[TenantLog]]:
    db_engine = PluginManager().dbPlugin
    tenant_log = await db_engine.get_tenant_log(body, tenant.tenant_id)
    return ResponseModel(
        success=True,
        data=tenant_log,
        message="Success",
    )
