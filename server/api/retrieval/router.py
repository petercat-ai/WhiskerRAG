from typing import List

from deprecated import deprecated
from fastapi import APIRouter, Depends
from whiskerrag_types.model import (RetrievalByKnowledgeRequest,
                                    RetrievalBySpaceRequest, RetrievalChunk,
                                    Tenant)
from whiskerrag_types.model.retrieval import RetrievalRequest

from core.auth import Action, Resource, get_tenant_with_permissions
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from core.retrieval_counter import (RetrievalCounter, get_retrieval_counter,
                                    retrieval_count)

router = APIRouter(
    prefix="/api/retrieval",
    tags=["retrieval"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/knowledge",
    operation_id="retrieve_knowledge_content",
    response_model_by_alias=False,
    response_model_exclude_none=True,
)
async def retrieve_knowledge_content(
    body: RetrievalByKnowledgeRequest,
    tenant: Tenant = get_tenant_with_permissions(Resource.RETRIEVAL, [Action.READ]),
    counter: RetrievalCounter = Depends(get_retrieval_counter),
) -> ResponseModel[List[RetrievalChunk]]:
    """
    Retrieve certain chunks within a knowledge_id, for example, within a specific PDF file.
    """
    db_engine = PluginManager().dbPlugin
    res = await db_engine.search_knowledge_chunk_list(tenant.tenant_id, body)
    retrieval_count(counter, res)
    return ResponseModel(success=True, data=res)


@deprecated("retrieve_space_content is deprecated, please use retrieve instead.")
@router.post(
    "/space",
    operation_id="retrieve_space_content",
    response_model_by_alias=False,
    response_model_exclude_none=True,
)
async def retrieve_space_content(
    body: RetrievalBySpaceRequest,
    tenant: Tenant = get_tenant_with_permissions(Resource.RETRIEVAL, [Action.READ]),
    counter: RetrievalCounter = Depends(get_retrieval_counter),
) -> ResponseModel[List[RetrievalChunk]]:
    """
    Retrieve chunks within a space_id, for example, given a petercat bot_id, retrieve all chunks under that bot_id.
    """
    db_engine = PluginManager().dbPlugin
    res = await db_engine.search_space_chunk_list(tenant.tenant_id, body)
    retrieval_count(counter, res)
    return ResponseModel(success=True, data=res)


@router.post(
    "/",
    operation_id="retrieve",
    response_model_by_alias=False,
    response_model_exclude_none=True,
)
async def retrieve(
    body: RetrievalRequest,
    tenant: Tenant = get_tenant_with_permissions(Resource.RETRIEVAL, [Action.READ]),
    counter: RetrievalCounter = Depends(get_retrieval_counter),
) -> ResponseModel[List[RetrievalChunk]]:
    """
    Retrieve chunks within a space_id, for example, given a petercat bot_id, retrieve all chunks under that bot_id.
    """
    db_engine = PluginManager().dbPlugin
    res = await db_engine.retrieve(tenant.tenant_id, body)
    retrieval_count(counter, res)
    return ResponseModel(success=True, data=res)
