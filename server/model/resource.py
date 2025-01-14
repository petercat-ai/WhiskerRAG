from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Union




# 基础资源模型
class BaseKnowledgeResourceModel(BaseModel):
    knowledge_name: str = Field(..., description="knowledge name")
    embedding_model_name: Optional[str] = Field(
        None, description="embedding model name"
    )
    split_config: Optional[dict] = Field(None, description="split config")
    metadata: Optional[dict] = Field(None, description="metadata")
    sha: Optional[str] = Field(None, description="resource sha")


# 文本资源模型
class TextResourceModel(BaseKnowledgeResourceModel):
    source_data: Optional[dict] = Field(None, description="file source info")
    type: ResourceType = Field(ResourceType.TEXT, description="file type")


# 文件资源模型
class FileResourceModel(BaseKnowledgeResourceModel):
    source_url: Optional[dict] = Field(None, description="file source url")
    type: ResourceType = Field(default=None, description="file type")


# PDF资源模型
class PDFResourceModel(FileResourceModel):
    type: ResourceType = Field(ResourceType.PDF, description="file type")


# 图片资源模型
class ImageResourceModel(FileResourceModel):
    type: ResourceType = Field(ResourceType.IMAGE, description="file type")


# GITHUB 资源模型
class GitHubFileResourceModel(FileResourceModel):
    type: ResourceType = Field(ResourceType.GITHUB_FILE, description="file type")


# GITHUB 仓库资源模型
class GitHubRepoResourceModel(FileResourceModel):
    type: ResourceType = Field(ResourceType.GITHUB_REPO, description="file type")
    # 分支名
    branch_name: Optional[str] = Field(None, description="github branch name")


# MARKDOWN 资源模型
class MarkdownResourceModel(FileResourceModel):
    type: ResourceType = Field(ResourceType.MARKDOWN, description="file type")


# 资源入库请求模型
class ResourceEmbeddingRequest(BaseModel):
    spaceId: str = Field(..., description="space id")
    # 资源信息
    resourceList: list[
        Union[
            TextResourceModel,
            MarkdownResourceModel,
            GitHubRepoResourceModel,
            GitHubFileResourceModel,
            PDFResourceModel,
            ImageResourceModel,
        ]
    ] = Field(..., description="resource info", discriminator="type")
