from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from whiskerrag_types.model import ProResearchRequest
from core.plugin_manager import PluginManager
from whiskerrag_types.model import Tenant
from core.auth import Action, Resource, get_tenant_with_permissions
import logging

logger = logging.getLogger("whisker")

router = APIRouter(
    prefix="/v1/api/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}},
)


@router.post("/pro_research")
async def pro_research(
    body: ProResearchRequest,
    tenant: Tenant = get_tenant_with_permissions(Resource.CHUNK, [Action.READ]),
):
    logger.info(
        f"type:pro_research - tenant: {tenant.tenant_id} - body: {body.messages}"
    )
    db_engine = PluginManager().dbPlugin
    return StreamingResponse(
        db_engine.agent_invoke(body), media_type="text/event-stream"
    )
