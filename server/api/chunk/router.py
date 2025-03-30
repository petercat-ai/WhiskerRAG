from core.auth import get_tenant
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Depends
from whiskerrag_types.model import Chunk, PageParams, PageResponse, Tenant

router = APIRouter(
    prefix="/api/chunk",
    tags=["chunk"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_tenant)],
)


@router.post(
    "/list",
    operation_id="get_chunk_list",
)
async def get_chunk_list(
    body: PageParams[Chunk], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Chunk]]:
    db_engine = PluginManager().dbPlugin
    chunks: PageResponse[Chunk] = await db_engine.get_chunk_list(tenant.tenant_id, body)
    return ResponseModel(data=chunks, success=True)
