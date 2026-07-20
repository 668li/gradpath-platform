"""导师评价表模型 — 学生对导师的真实评价。

核心字段：
- 6 维评分：学术水平/指导风格/师生关系/科研经费/工作强度/毕业前景
- 文字评价：标题 + 详细内容
- 审核机制：待审核/已通过/已拒绝
- 防刷评：同 IP 30 天限制
- 匿名机制：可选择匿名评价
"""
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class MentorReview(UUIDMixin, TimestampMixin, Base):
    """导师评价表 — 存储学生对导师的真实评价。"""
    __tablename__ = "mentor_reviews"

    # === 关联 ===
    mentor_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("mentors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # === 匿名机制 ===
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    anonymous_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 匿名标识（如"2023级硕士"）
    
    # === 6 维评分（1-5 分）===
    rating_academic: Mapped[int] = mapped_column(Integer, nullable=False)  # 学术水平
    rating_guidance: Mapped[int] = mapped_column(Integer, nullable=False)  # 指导风格
    rating_relationship: Mapped[int] = mapped_column(Integer, nullable=False)  # 师生关系
    rating_funding: Mapped[int] = mapped_column(Integer, nullable=False)  # 科研经费
    rating_workload: Mapped[int] = mapped_column(Integer, nullable=False)  # 工作强度（1=轻松, 5=996）
    rating_career: Mapped[int] = mapped_column(Integer, nullable=False)  # 毕业前景
    
    # 综合评分（自动计算）
    overall_rating: Mapped[float] = mapped_column(Float, nullable=False)
    
    # === 文字评价 ===
    title: Mapped[str] = mapped_column(String(200), nullable=False)  # 评价标题
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 详细评价内容
    
    # === 标签化评价 ===
    pros: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 优点标签 ["学术能力强", "指导细致"]
    cons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 缺点标签 ["工作强度大", "沟通少"]
    
    # === 审核机制 ===
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending/approved/rejected
    
    # === 互动数据 ===
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 是否有帮助（用户标记）
    
    # === 防刷评 ===
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    submitted_at: Mapped[str] = mapped_column(String(50), nullable=False)  # 提交时间戳（用于 30 天限制检查）
    
    # === 元数据 ===
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 是否已验证（如提交学生证）
    verification_proof: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 验证材料路径
    reviewer_identity: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 评价者身份（如"2023级硕士毕业生"）
