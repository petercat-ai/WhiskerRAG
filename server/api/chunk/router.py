from fastapi import APIRouter, Depends
from whiskerrag_types.model import (
    Tenant,
    PageParams,
    Chunk,
    PageResponse,
    Knowledge,
)

from core.auth import get_tenant, require_auth
from core.plugin_manager import PluginManager
from core.response import ResponseModel

router = APIRouter(
    prefix="/api/chunk",
    tags=["chunk"],
    responses={404: {"description": "Not found"}},
)


@router.post("/list")
@require_auth()
async def get_chunk_list(
    body: PageParams[Chunk], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Chunk]]:
    db_engine = PluginManager().dbPlugin
    chunks: PageResponse[Knowledge] = await db_engine.get_chunk_list(
        tenant.tenant_id, body
    )
    return ResponseModel(data=chunks, success=True)
