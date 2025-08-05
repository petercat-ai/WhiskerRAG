import logging
from typing import List

from fastapi import APIRouter
from whiskerrag_types.model import (
    PageQueryParams,
    StatusStatisticsPageResponse,
    Task,
    TaskRestartRequest,
    TaskStatus,
    Tenant,
)

from core.auth import Action, Resource, get_tenant_with_permissions
from core.plugin_manager import PluginManager
from core.response import ResponseModel

router = APIRouter(
    prefix="/api/task", tags=["task"], responses={404: {"description": "Not found"}}
)

logger = logging.getLogger("whisker")


@router.post("/restart", operation_id="restart_task", response_model_by_alias=False)
async def restart_task(
    request: TaskRestartRequest,
    tenant: Tenant = get_tenant_with_permissions(Resource.TASK, [Action.UPDATE]),
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
            logger.error(f"Task {task_id} not found")
            continue
        knowledge = await db_engine.get_knowledge(tenant.tenant_id, task.knowledge_id)
        if not knowledge:
            logger.error(f"Knowledge {task.knowledge_id} not found")
            continue
        task.update(status=TaskStatus.PENDING_RETRY)
        restart_task.append(task)
        restart_knowledge.append(knowledge)
    await db_engine.update_task_list(restart_task)
    if restart_task:
        await task_engine.batch_execute_task(restart_task, restart_knowledge)
    else:
        logger.info("No task to restart")
    return ResponseModel(data=restart_task, success=True)


@router.post("/cancel", operation_id="cancel_task")
async def cancel_task(
    request: TaskRestartRequest,
    tenant: Tenant = get_tenant_with_permissions(Resource.TASK, [Action.UPDATE]),
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
    body: PageQueryParams[Task],
    tenant: Tenant = get_tenant_with_permissions(Resource.TASK, [Action.READ]),
) -> ResponseModel[StatusStatisticsPageResponse[Task]]:
    db_engine = PluginManager().dbPlugin
    res = await db_engine.get_task_list(tenant.tenant_id, body)
    return ResponseModel(data=res, success=True)


@router.get("/detail", operation_id="get_task_detail", response_model_by_alias=False)
async def get_task_detail(
    task_id: str,
    tenant: Tenant = get_tenant_with_permissions(Resource.TASK, [Action.READ]),
) -> ResponseModel[Task]:
    db_engine = PluginManager().dbPlugin
    res = await db_engine.get_task_by_id(
        tenant.tenant_id,
        task_id,
    )
    return ResponseModel(data=res, success=True)


@router.delete("/delete", operation_id="delete_task_by_id")
async def delete_task_by_id(
    task_id: str,
    tenant: Tenant = get_tenant_with_permissions(Resource.TASK, [Action.DELETE]),
) -> ResponseModel[Task]:
    db_engine = PluginManager().dbPlugin
    res = await db_engine.delete_task_by_id(
        tenant.tenant_id,
        task_id,
    )
    return ResponseModel(data=res, success=True)
