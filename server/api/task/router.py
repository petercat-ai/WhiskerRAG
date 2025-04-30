from typing import List

from core.auth import get_tenant
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Depends
from whiskerrag_types.model import (
    PageParams,
    PageResponse,
    StatusStatisticsPageResponse,
    Task,
    TaskRestartRequest,
    TaskStatus,
    Tenant,
)

router = APIRouter(
    prefix="/api/task",
    tags=["task"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_tenant)],
)


@router.post("/restart", operation_id="restart_task", response_model_by_alias=False)
async def restart_task(
    request: TaskRestartRequest,
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[List[Task]]:
    db_engine = PluginManager().dbPlugin
    task_engine = PluginManager().taskPlugin
    restart_task = []
    restart_knowledge = []
    for task_id in request.task_id_list:
        task = await db_engine.get_task_by_id(
            tenant.tenant_id,
            task_id,
        )
        if not task:
            continue
        knowledge = await db_engine.get_knowledge(tenant.tenant_id, task.knowledge_id)
        if not knowledge:
            continue
        task.update(status=TaskStatus.PENDING_RETRY)
        restart_task.append(task)
        restart_knowledge.append(knowledge)
    await db_engine.update_task_list(restart_task)
    await task_engine.batch_execute_task(restart_task, restart_knowledge)
    return ResponseModel(data=restart_task, success=True)


@router.post("/cancel", operation_id="cancel_task")
async def cancel_task(
    request: TaskRestartRequest,
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[List[Task]]:
    db_engine = PluginManager().dbPlugin
    cancel_task = []
    for task_id in request.task_id_list:
        task = await db_engine.get_task_by_id(
            tenant.tenant_id,
            task_id,
        )
        if not task:
            continue
        task.update(status=TaskStatus.CANCELED)
        cancel_task.append(task)
    await db_engine.update_task_list(cancel_task)
    return ResponseModel(data=cancel_task, success=True)


@router.post("/list", operation_id="get_task_list")
async def get_task_list(
    body: PageParams[Task], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[StatusStatisticsPageResponse[Task]]:
    db_engine = PluginManager().dbPlugin
    res: PageResponse[Task] = await db_engine.get_task_list(tenant.tenant_id, body)
    statistics = await db_engine.task_statistics(
        body.eq_conditions.get("space_id", None), None
    )
    res: StatusStatisticsPageResponse[Task] = StatusStatisticsPageResponse(
        **res.model_dump()
    )
    res.success = statistics.get(TaskStatus.SUCCESS, 0)
    res.failed = statistics.get(TaskStatus.FAILED, 0)
    res.cancelled = statistics.get(TaskStatus.CANCELED, 0)
    return ResponseModel(data=res, success=True)


@router.get("/detail", operation_id="get_task_detail", response_model_by_alias=False)
async def get_task_detail(
    task_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[Task]:
    db_engine = PluginManager().dbPlugin
    res = await db_engine.get_task_by_id(
        tenant.tenant_id,
        task_id,
    )
    return ResponseModel(data=res, success=True)


@router.delete("/delete", operation_id="delete_task_by_id")
async def delete_task_by_id(
    task_id: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[Task]:
    db_engine = PluginManager().dbPlugin
    res = await db_engine.delete_task_by_id(
        tenant.tenant_id,
        task_id,
    )
    return ResponseModel(data=res, success=True)
