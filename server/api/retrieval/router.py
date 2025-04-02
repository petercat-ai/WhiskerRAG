from typing import List

from core.auth import get_tenant
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Depends
from whiskerrag_types.model import (
    RetrievalByKnowledgeRequest,
    RetrievalBySpaceRequest,
    RetrievalChunk,
    Tenant,
)

router = APIRouter(
    prefix="/api/retrieval",
    tags=["retrieval"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_tenant)],
)


@router.post(
    "/knowledge",
    operation_id="retrieve_knowledge_content",
    response_model_by_alias=False,
)
async def retrieve_knowledge_content(
    body: RetrievalByKnowledgeRequest,
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[List[RetrievalChunk]]:
    """
    Retrieve certain chunks within a knowledge_id, for example, within a specific PDF file.
    """
    db_engine = PluginManager().dbPlugin
    res = await db_engine.search_knowledge_chunk_list(tenant.tenant_id, body)
    return ResponseModel(success=True, data=res)


@router.post(
    "/space", operation_id="retrieve_space_content", response_model_by_alias=False
)
async def retrieve_space_content(
    body: RetrievalBySpaceRequest,
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[List[RetrievalChunk]]:
    """
    Retrieve chunks within a space_id, for example, given a petercat bot_id, retrieve all chunks under that bot_id.
    """
    db_engine = PluginManager().dbPlugin
    res = await db_engine.search_space_chunk_list(tenant.tenant_id, body)
    return ResponseModel(success=True, data=res)
