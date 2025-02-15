from asyncio import Task
from typing import List
from fastapi import APIRouter, Depends
from whiskerrag_types.model import PageParams, PageResponse, Tenant

from core.auth import get_tenant, require_auth
from core.response import ResponseModel
from core.plugin_manager import PluginManager

router = APIRouter(
    prefix="/api/task",
    tags=["task"],
    responses={404: {"description": "Not found"}},
)


@router.post("/list")
@require_auth()
async def get_task_list(
    body: PageParams, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel:
    db_engine = PluginManager().dbPlugin
    task_list: PageResponse[Task] = await db_engine.get_task_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=task_list, success=True)
