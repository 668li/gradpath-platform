"""导师相关 Pydantic schemas"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# === 导师基础信息 ===
class MentorBase(BaseModel):
    # 修复: FASTAPI-VALID-001 — 字符串字段加 max_length 防止超长输入
    name: str = Field(..., min_length=1, max_length=100, description="导师姓名")
    university: str = Field(..., min_length=1, max_length=200, description="所属院校")
    department: str = Field(..., min_length=1, max_length=200, description="所属院系")
    title: str = Field(..., min_length=1, max_length=100, description="职称")
    research_directions: List[str] = Field(default=[], description="研究方向")
    paper_count: int = Field(default=0, description="论文数量")
    project_count: int = Field(default=0, description="项目数量")
    citation_count: int = Field(default=0, description="引用次数")
    h_index: Optional[int] = Field(None, description="h-index")
    academic_homepage: Optional[str] = Field(None, max_length=2000, description="学术主页链接")
    google_scholar_url: Optional[str] = Field(None, max_length=2000, description="Google Scholar 链接")
    cnki_url: Optional[str] = Field(None, max_length=2000, description="知网主页链接")
    enrollment_status: str = Field(default="unknown", max_length=50, description="招生状态")
    enrollment_directions: List[str] = Field(default=[], description="招生方向")
    contact_email: Optional[str] = Field(None, max_length=200, description="联系邮箱")
    contact_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    source_url: Optional[str] = Field(None, max_length=2000, description="数据来源 URL")
    source_platform: str = Field(default="official", max_length=50, description="数据来源平台")
    tags: List[str] = Field(default=[], description="标签")


class MentorCreate(MentorBase):
    """创建导师"""
    pass


class MentorUpdate(BaseModel):
    """更新导师信息"""
    name: Optional[str] = None
    university: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    research_directions: Optional[List[str]] = None
    paper_count: Optional[int] = None
    project_count: Optional[int] = None
    citation_count: Optional[int] = None
    h_index: Optional[int] = None
    academic_homepage: Optional[str] = None
    google_scholar_url: Optional[str] = None
    cnki_url: Optional[str] = None
    enrollment_status: Optional[str] = None
    enrollment_directions: Optional[List[str]] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    tags: Optional[List[str]] = None


class MentorResponse(MentorBase):
    """导师响应"""
    id: UUID
    avg_rating: float = Field(..., description="平均评分")
    review_count: int = Field(..., description="评价数量")
    rating_academic: float = Field(..., description="学术水平评分")
    rating_guidance: float = Field(..., description="指导风格评分")
    rating_relationship: float = Field(..., description="师生关系评分")
    rating_funding: float = Field(..., description="科研经费评分")
    rating_workload: float = Field(..., description="工作强度评分")
    rating_career: float = Field(..., description="毕业前景评分")
    is_verified: bool = Field(..., description="是否已验证")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === 导师评价 ===
class MentorReviewBase(BaseModel):
    rating_academic: int = Field(..., ge=1, le=5, description="学术水平评分 1-5")
    rating_guidance: int = Field(..., ge=1, le=5, description="指导风格评分 1-5")
    rating_relationship: int = Field(..., ge=1, le=5, description="师生关系评分 1-5")
    rating_funding: int = Field(..., ge=1, le=5, description="科研经费评分 1-5")
    rating_workload: int = Field(..., ge=1, le=5, description="工作强度评分 1-5")
    rating_career: int = Field(..., ge=1, le=5, description="毕业前景评分 1-5")
    # 修复: FASTAPI-VALID-001 — 评价 title/content 加 max_length
    title: str = Field(..., min_length=1, max_length=200, description="评价标题")
    content: str = Field(..., min_length=1, max_length=20000, description="详细评价内容")
    pros: List[str] = Field(default=[], description="优点标签")
    cons: List[str] = Field(default=[], description="缺点标签")
    is_anonymous: bool = Field(default=True, description="是否匿名")
    anonymous_id: Optional[str] = Field(None, max_length=100, description="匿名标识")
    reviewer_identity: Optional[str] = Field(None, max_length=200, description="评价者身份")


class MentorReviewCreate(MentorReviewBase):
    """创建导师评价"""
    mentor_id: Optional[UUID] = Field(None, description="导师 ID（可选，URL 路径中已包含）")


class MentorReviewResponse(MentorReviewBase):
    """导师评价响应"""
    id: UUID
    mentor_id: UUID
    user_id: UUID
    overall_rating: float = Field(..., description="综合评分")
    review_status: str = Field(..., description="审核状态")
    like_count: int = Field(..., description="点赞数")
    is_helpful: bool = Field(..., description="是否有帮助")
    submitted_at: str = Field(..., description="提交时间")
    is_verified: bool = Field(..., description="是否已验证")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MentorReviewListResponse(BaseModel):
    """导师评价列表响应"""
    items: List[MentorReviewResponse]
    total: int
    page: int
    page_size: int


# === 导师列表响应 ===
class MentorListResponse(BaseModel):
    """导师列表响应"""
    items: List[MentorResponse]
    total: int
    page: int
    page_size: int
