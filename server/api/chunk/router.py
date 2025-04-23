import uuid
from http.client import HTTPException
from typing import List, Optional

from pydantic import BaseModel
from whiskerrag_utils import get_register, RegisterTypeEnum

from core.auth import get_tenant
from core.log import logger
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


class ChunkSave(BaseModel):
    chunk_id: Optional[str] = None
    space_id: str
    context: str
    knowledge_id: str
    embedding_model_name: str
    metadata: Optional[dict] = None


@router.post("/list", operation_id="get_chunk_list", response_model_by_alias=False)
async def get_chunk_list(
    params: PageParams[Chunk], tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[PageResponse[Chunk]]:
    logger.info("[chunk][list][start], req={}".format(params))
    try:
        db_engine = PluginManager().dbPlugin
        params.eq_conditions["tenant_id"] = tenant.tenant_id
        chunks: PageResponse[Chunk] = await db_engine.get_chunk_list(
            tenant.tenant_id, params
        )
        logger.info("[chunk][list][end]")
        return ResponseModel(data=chunks, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"[chunk][list][error], req={params}, error={str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="获取分块列表失败")


@router.delete(
    "/id/{id}/model_name/{model_name}",
    operation_id="delete_chunk_by_id",
    response_model_by_alias=False,
)
async def delete_chunk_by_id(
    id: str, model_name: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[object]:
    logger.info(f"[chunk][delete][start], id={id}, model={model_name}")
    try:
        db_engine = PluginManager().dbPlugin
        result = await db_engine.delete_chunk_by_id(tenant.tenant_id, id, model_name)
        if not result:
            raise HTTPException(status_code=404, detail="分块不存在")
        logger.info("[chunk][delete][end]")
        return ResponseModel(data=True, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[chunk][delete][error], id={id}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除分块失败")


@router.get(
    "/id/{id}/model_name/{model_name}",
    operation_id="get_chunk_by_id",
    response_model_by_alias=False,
)
async def get_chunk_by_id(
    id: str, model_name: str, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[Chunk]:
    logger.info(f"[chunk][detail][start], id={id}, model={model_name}")
    try:
        db_engine = PluginManager().dbPlugin
        chunk: Chunk = await db_engine.get_chunk_by_id(tenant.tenant_id, id, model_name)
        if not chunk:
            raise HTTPException(status_code=404, detail="分块不存在")
        logger.info("[chunk][detail][end]")
        return ResponseModel(data=chunk, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[chunk][detail][error], id={id}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取分块详情失败")


@router.post("/save", operation_id="save_chunk", response_model_by_alias=False)
async def save_chunk(
    params: ChunkSave, tenant: Tenant = Depends(get_tenant)
) -> ResponseModel[Chunk]:
    logger.info("[chunk][save][start], req={}".format(params))
    try:
        db_engine = PluginManager().dbPlugin
        embedding_model = get_register(
            RegisterTypeEnum.EMBEDDING, params.embedding_model_name
        )

        # 生成唯一ID逻辑
        is_insert = False
        if not params.chunk_id:
            params.chunk_id = str(uuid.uuid4())
            is_insert = True

        # 构建分块对象
        chunk = Chunk(
            chunk_id=params.chunk_id,
            space_id=params.space_id,
            context=params.context,
            knowledge_id=params.knowledge_id,
            embedding_model_name=params.embedding_model_name,
            metadata=params.metadata,
            tenant_id=tenant.tenant_id,
            embedding=await embedding_model().embed_text(params.context, 10),
        )

        # 更新逻辑
        if not is_insert:
            exist_chunk = await db_engine.get_chunk_by_id(
                tenant.tenant_id, params.chunk_id, params.embedding_model_name
            )
            if not exist_chunk:
                raise HTTPException(status_code=404, detail="分块不存在")
            # 字段合并逻辑
            for field in Chunk.__fields__:
                if getattr(chunk, field) is None:
                    setattr(chunk, field, getattr(exist_chunk, field))

        # 保存操作
        saved_chunks: List[Chunk] = await db_engine.save_chunk_list([chunk])
        logger.info("[chunk][save][end]")
        return ResponseModel(data=saved_chunks[0], success=True)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(
            f"[chunk][save][error], req={params}, error={str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="保存分块失败")
