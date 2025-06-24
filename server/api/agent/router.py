from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from whiskerrag_types.model import ProResearchRequest
from core.plugin_manager import PluginManager


router = APIRouter(
    prefix="/v1/api/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}},
)


@router.post("/pro_research")
async def pro_research(body: ProResearchRequest):
    db_engine = PluginManager().dbPlugin
    return StreamingResponse(db_engine.agent_invoke(body))
