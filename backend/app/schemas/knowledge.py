# backend/app/schemas/knowledge.py
"""知识库条目的 Pydantic Schema 定义。

注意：模型中字段名为 ``metadata_``（因 ``metadata`` 被 SQLAlchemy 保留），
对应数据库列 ``metadata``。Schema 统一使用 ``metadata_`` 字段名对外暴露。
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeArticleBase(BaseModel):
    category: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    # 修复: FASTAPI-VALID-001 — content 加 max_length 防止超大文本攻击
    content: str = Field(..., min_length=1, max_length=100000)
    tags: list[str] = Field(default_factory=list)
    source: str | None = Field(None, max_length=200)
    metadata_: dict = Field(default_factory=dict)
    is_published: bool = True


class KnowledgeArticleCreate(KnowledgeArticleBase):
    pass


class KnowledgeArticleUpdate(BaseModel):
    category: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=200)
    content: str | None = Field(None, min_length=1, max_length=100000)
    tags: list[str] | None = None
    source: str | None = Field(None, max_length=200)
    metadata_: dict | None = None
    is_published: bool | None = None


class KnowledgeArticleResponse(BaseModel):
    id: UUID
    category: str
    title: str
    content: str
    tags: list[str]
    source: str | None
    metadata_: dict
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
