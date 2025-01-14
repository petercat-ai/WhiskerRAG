from dataclasses import Field
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_serializer, Field


# 资源类型枚举,对应了不同的资源解析方式
class ResourceType(str, Enum):
    GITHUB_REPO = ("github_repo",)
    GITHUB_FILE = ("github_file",)
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"


class KnowledgeSplitConfig(BaseModel):
    split_regex: str = Field(description="split regex")
    chunk_size: int = Field(description="chunk size")
    chunk_overlap: int = Field(description="chunk overlap")


class Knowledge(BaseModel):
    knowledge_id: str = Field(None, description="knowledge id")
    knowledge_name: str = Field(description="knowledge name")
    knowledge_type: ResourceType = Field(description="knowledge type")
    """ file sha value """
    sha: Optional[str] = Field(None, description="resource sha")
    split_config: Optional[KnowledgeSplitConfig] = Field(
        None, description="split config"
    )
    source_data: Optional[str] = Field(None, description="file source info")
    source_url: Optional[str] = Field(None, description="file source info")
    auth_info: Optional[str] = Field(None, description="file auth info")
    embedding_model_name: Optional[str] = Field(None, description="file source info")
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now().isoformat(), description="creation time"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now().isoformat(), description="update time"
    )
    space_id: str = Field(..., description="space id")
    tenant_id: str = Field(..., description="tenant id")
    metadata: Optional[dict] = Field(None, description="metadata")

    @field_serializer("created_at")
    def serialize_created_at(self, created_at: Optional[datetime]):
        return created_at.isoformat() if created_at else None

    @field_serializer("updated_at")
    def serialize_updated_at(self, updated_at: Optional[datetime]):
        return updated_at.isoformat() if updated_at else None

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        # 设置更新时间
        self.updated_at = datetime.now().isoformat()
        return self
