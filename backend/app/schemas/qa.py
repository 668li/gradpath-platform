"""考研问答 Pydantic schemas"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === 问答基础信息 ===
class QABase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="问题标题")
    # 修复: FASTAPI-VALID-001 — content 加 max_length 防止超大文本攻击（存储/带宽/索引）
    content: str = Field(..., min_length=1, max_length=20000, description="问题详情")
    tags: list[str] = Field(default_factory=list, description="标签")


class QACreate(QABase):
    """创建问题"""
    pass


class QAUpdate(BaseModel):
    """更新问题"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=20000)
    tags: Optional[list[str]] = None


# === 回答基础信息 ===
class QAAnswerBase(BaseModel):
    # 修复: FASTAPI-VALID-001 — 回答内容加 max_length
    content: str = Field(..., min_length=1, max_length=20000, description="回答内容")


class QAAnswerCreate(QAAnswerBase):
    """创建回答"""
    pass


class QAAnswerUpdate(BaseModel):
    """更新回答"""
    content: Optional[str] = Field(None, min_length=1, max_length=20000)


class QAAnswerResponse(QAAnswerBase):
    """回答响应"""
    id: UUID
    qa_id: UUID
    user_id: UUID
    is_best: bool = Field(..., description="是否为最佳回答")
    like_count: int = Field(..., description="点赞数")
    status: str = Field(..., description="审核状态")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QAResponse(QABase):
    """问题响应"""
    id: UUID
    user_id: UUID
    status: str = Field(..., description="审核状态")
    view_count: int = Field(..., description="浏览数")
    answer_count: int = Field(..., description="回答数")
    is_resolved: bool = Field(..., description="是否已解决")
    best_answer_id: Optional[UUID] = Field(None, description="最佳回答 ID")
    answers: list[QAAnswerResponse] = Field(default_factory=list, description="回答列表")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QAListResponse(BaseModel):
    """问题列表响应"""
    items: list[QAResponse]
    total: int
    page: int
    page_size: int


class QAAnswerListResponse(BaseModel):
    """回答列表响应"""
    items: list[QAAnswerResponse]
    total: int
    page: int
    page_size: int
