from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from whiskerrag_types.model import ProResearchRequest
from core.plugin_manager import PluginManager
from whiskerrag_types.model import Tenant
from core.auth import Action, Resource, get_tenant_with_permissions
import logging
import asyncio

logger = logging.getLogger("whisker")

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}},
)


@router.post("/pro_research")
async def pro_research(
    body: ProResearchRequest,
    request: Request,
    tenant: Tenant = get_tenant_with_permissions(Resource.CHUNK, [Action.READ]),
):
    logger.info(
        f"type:pro_research - tenant: {tenant.tenant_id} - body: {body.messages}"
    )
    db_engine = PluginManager().dbPlugin

    # Create a cancellation event that will be triggered when client disconnects
    cancellation_event = asyncio.Event()

    # Create the cancellable agent iterator
    async def cancellable_agent_iterator():
        try:
            async for chunk in db_engine.agent_invoke(body, cancellation_event):
                # Check if client is still connected
                if await request.is_disconnected():
                    logger.info("Client disconnected, cancelling agent execution")
                    cancellation_event.set()
                    break
                yield chunk
        except asyncio.CancelledError:
            logger.info("Agent execution was cancelled")
            cancellation_event.set()
            # Send cancellation notification
            yield b'data: {"type": "cancelled", "message": "Agent execution cancelled"}\n\n'
            raise
        except Exception as e:
            logger.error(f"Error in cancellable_agent_iterator: {e}")
            cancellation_event.set()
            raise
        finally:
            # Ensure cancellation event is set for cleanup
            cancellation_event.set()

    return StreamingResponse(
        cancellable_agent_iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
