from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter
from typing import List, Optional

from core.log import logger
from core.plugin_manager import PluginManager
from core.sha_util import calculate_sha256
from model.response import ResponseModel
from whisker_rag_type.model.knowledge import Knowledge, ResourceType


router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)


class KnowledgeCreate(BaseModel):
    knowledge_type: ResourceType
    space_id: str = None
    knowledge_name: str
    sha: Optional[str] = None
    split_config: Optional[dict] = None
    source_data: Optional[str] = None
    source_url: Optional[str] = None
    auth_info: Optional[str] = None
    embedding_model_name: Optional[str] = None
    metadata: Optional[dict] = None


class KnowledgeResponse(BaseModel):
    knowledge_id: Optional[str] = None
    space_id: str = None
    knowledge_name: str
    sha: Optional[str] = None
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    space_id: str
    tenant_id: str

    @classmethod
    def from_db_record(cls, record: dict):
        """
        从 Supabase 查询记录转换为 Pydantic 模型

        :param record: Supabase 查询返回的单条记录
        :return: KnowledgeResponse 实例
        """
        return cls(
            knowledge_id=record.get("knowledge_id"),
            knowledge_name=record.get("knowledge_name"),
            sha=record.get("sha"),
            source_url=record.get("source_url"),
            created_at=record.get("created_at"),
            updated_at=record.get("created_at"),
            space_id=record.get("space_id"),
            tenant_id=record.get("tenant_id"),
        )


@router.post("/test/sqs")
async def add_knowledge(body: dict) -> ResponseModel:
    task = PluginManager().taskPlugin
    task.test(body)


@router.post("/add")
async def add_knowledge(body: List[KnowledgeCreate]) -> ResponseModel:
    db = PluginManager().dbPlugin
    knowledge_list = []
    for item in body:
        if not item.sha:
            item.sha = calculate_sha256(item.source_data)
        # TODO: 从 header 中置换出 tenant cloud user id
        item = Knowledge(
            **item.dict(), tenant_id="a5c5f741-6274-4118-aed2-3336ddfad618"
        )
        knowledge_list.append(item)
    res = await db.add_knowledge(knowledge_list)
    knowledge_list = [KnowledgeResponse.from_db_record(record) for record in res]
    logger.info(f"Knowledge added successfully: {knowledge_list}")
    # TODO: 交给 任务引擎，异步执行知识拆分和向量索引构建
    task = PluginManager().taskPlugin
    # TODO: user_id
    await task.embed_knowledge_list("", knowledge_list)
    return ResponseModel[List[KnowledgeResponse]](success=True, data=knowledge_list)
