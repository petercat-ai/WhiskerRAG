from dataclasses import Field
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_serializer, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Task(BaseModel):
    task_id: str = Field(None, description="task id")
    status: TaskStatus = Field(None, description="task status")
    knowledge_id: str = Field(None, description="file source info")
    space_id: str = Field(..., description="space id")
    user_id: Optional[str] = Field(None, description="user id")
    tenant_id: str = Field(..., description="tenant id")
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now().isoformat(), description="creation time"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now().isoformat(), description="update time"
    )

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
