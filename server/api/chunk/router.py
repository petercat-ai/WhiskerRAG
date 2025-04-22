from typing import List

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


@router.post("/list", operation_id="get_chunk_list", response_model_by_alias=False)
async def get_chunk_list(
    body: PageParams[Chunk], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Chunk]]:
    db_engine = PluginManager().dbPlugin
    chunks: PageResponse[Chunk] = await db_engine.get_chunk_list(tenant.tenant_id, body)
    return ResponseModel(data=chunks, success=True)


@router.delete(
    "/id/{id}/model_name/{model_name}",
    operation_id="delete_chunk_by_id",
    response_model_by_alias=False,
)
async def delete_chunk_by_id(
    id: str, model_name: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[object]:
    db_engine = PluginManager().dbPlugin
    chunks: PageResponse[Chunk] = await db_engine.delete_chunk_by_id(
        tenant.tenant_id, id, model_name
    )
    return ResponseModel(data=chunks, success=True)


@router.get(
    "/id/{id}/model_name/{model_name}",
    operation_id="get_chunk_by_id",
    response_model_by_alias=False,
)
async def get_chunk_by_id(
    id: str, model_name: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Chunk]]:
    db_engine = PluginManager().dbPlugin
    chunks: PageResponse[Chunk] = await db_engine.get_chunk_by_id(
        tenant.tenant_id, id, model_name
    )
    return ResponseModel(data=chunks, success=True)


@router.post("/save", operation_id="save_chunk", response_model_by_alias=False)
async def save_chunk(
    body: Chunk, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Chunk]]:
    db_engine = PluginManager().dbPlugin
    # 如果传入chunkId则为修改
    if body.chunk_id:
        chunk = await db_engine.get_chunk_by_id(
            tenant.tenant_id, body.chunk_id, body.embedding_model_name
        )
        for field_name in body.keys():
            if getattr(body, field_name) is None:
                setattr(body, field_name, getattr(chunk, field_name))
    chunks: List[Chunk] = await db_engine.save_chunk_list([body], body)
    return ResponseModel(data=chunks[0], success=True)
