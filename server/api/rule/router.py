from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, HTTPException, Path
from whiskerrag_types.model import Tenant

router = APIRouter(
    prefix="/api/rule", tags=["rule"], responses={404: {"description": "Not found"}}
)


@router.get("/global", operation_id="get_global_rule", response_model_by_alias=False)
async def get_global_rule(
    tenant: Tenant = get_tenant_with_permissions(Resource.RULE, [Action.READ]),
) -> ResponseModel[str]:
    db_engine = PluginManager().dbPlugin
    rule = await db_engine.get_tenant_rule(tenant.tenant_id)
    if not rule:
        logger.error(
            "[get_tenant_rule][tenant rule not exists],tenant_id={}".format(
                tenant.tenant_id
            )
        )
        raise HTTPException(status_code=404, detail="knowledge base not exists")
    return ResponseModel(data=rule, success=True)


@router.get(
    "/space/{space_id}",
    operation_id="get_space_rule",
    response_model_by_alias=False,
)
async def get_space_rule(
    space_id: str = Path(..., description="knowledge base id"),
    tenant: Tenant = get_tenant_with_permissions(Resource.RULE, [Action.READ]),
) -> ResponseModel[str]:
    db_engine = PluginManager().dbPlugin
    rule = await db_engine.get_space_rule(tenant.tenant_id, space_id)
    if not rule:
        logger.error(
            "[get_space_rule][space rule not exists],tenant_id={}".format(
                tenant.tenant_id
            )
        )
        raise HTTPException(status_code=404, detail="knowledge base rule not exists")
    return ResponseModel(data=rule, success=True)
