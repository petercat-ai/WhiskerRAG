from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Path

from core.auth import Action, Resource, validate_key_string
from core.plugin_manager import PluginManager
from core.response import ResponseModel


router = APIRouter(
    prefix="/api/v1/webhook",
    tags=["webhook"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/{webhook_type}/{source}/{auth_info}/{knowledge_base_id}",
    status_code=200,
    summary="通用webhook处理器",
    description="whisker 通用 webhook",
    response_model_by_alias=False,
)
async def handle_webhook(
    webhook_type: str = Path(..., description="webhook type,eg:knowledge"),
    source: str = Path(..., description="webhook source,eg:github、yuque、gitlab"),
    auth_info: str = Path(..., description="auth info,such as ak、sk"),
    knowledge_base_id: str = Path(..., description="knowledge base id"),
    body: Dict[str, Any] = Body(..., description="webhook payload"),
):
    db_engine = PluginManager().dbPlugin
    (is_valid, tenant, error) = await validate_key_string(
        auth_info, Resource.KNOWLEDGE, [Action.ALL]
    )
    if not is_valid or not tenant:
        raise HTTPException(status_code=401, detail=error)
    res = await db_engine.handle_webhook(
        tenant=tenant,
        webhook_type=webhook_type,
        source=source,
        knowledge_base_id=knowledge_base_id,
        payload=body,
    )
    return ResponseModel(success=True, data=res)
