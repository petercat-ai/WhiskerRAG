from asyncio import Task

from core.auth import get_tenant, require_auth
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Depends
from whiskerrag_types.model import PageParams, PageResponse, Tenant

router = APIRouter(
    prefix="/api/task",
    tags=["task"],
    responses={404: {"description": "Not found"}},
)


@router.post("/list", operation_id="get_task_list")
@require_auth()
async def get_task_list(
    body: PageParams[Task], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel:
    db_engine = PluginManager().dbPlugin
    task_list: PageResponse[Task] = await db_engine.get_task_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=task_list, success=True)


@router.get("/detail", operation_id="get_task_detail")
@require_auth()
async def get_task_list(
    task_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel:
    db_engine = PluginManager().dbPlugin
    res = await db_engine.get_task_by_id(
        tenant.tenant_id,
        task_id,
    )
    return ResponseModel(data=res, success=True)
