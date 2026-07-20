"""用户长期记忆事实库 — AI 个性化护城河。

AI 从对话中自动抽取结构化事实（如"用户偏好金融行业""用户 GPA 3.8"），
下次调用时注入 system prompt，实现"AI 记得用户"的差异化体验。
"""
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class MemoryFactType(str, enum.Enum):
    """记忆事实类型 — 用于结构化分类与检索过滤。"""
    preference = "preference"        # 用户偏好（行业/城市/工作风格）
    background = "background"        # 用户背景（学校/GPA/技能）
    goal = "goal"                    # 用户目标（短期/长期）
    constraint = "constraint"        # 用户约束（家庭/经济/时间）
    behavior = "behavior"            # 用户行为模式（决策风格/反应模式）
    fact = "fact"                    # 客观事实（已发生的事件）


class UserMemoryFact(UUIDMixin, TimestampMixin, Base):
    """用户记忆事实 — AI 长期记忆的最小单元。

    设计原则：
    - 事实原子化：每条记录只表达一个事实，便于检索和更新
    - 置信度衰减：confidence 随时间和使用频率动态调整
    - 来源可追溯：source + conversation_id 记录事实来源，便于纠错
    - 反馈闭环：use_count + last_used_at 跟踪使用情况，user_feedback 接收反馈
    """
    __tablename__ = "user_memory_facts"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # === 事实结构 ===
    fact_type: Mapped[MemoryFactType] = mapped_column(
        Enum(MemoryFactType), nullable=False, index=True
    )
    # 事实键，如 "preferred_industry"、"gpa"、"target_school"
    fact_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # 事实值，如 "金融"、"3.8"、"清华大学"
    fact_value: Mapped[str] = mapped_column(Text, nullable=False)
    # 置信度 0-100，AI 抽取时给出，后续根据反馈调整
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=70)

    # === 来源追溯 ===
    # 来源：ai_extracted（AI 抽取）/ user_provided（用户主动告知）/ system_inferred（系统推断）
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="ai_extracted")
    conversation_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # === 使用追踪 ===
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === 用户反馈 ===
    # user_feedback: positive / negative / none
    user_feedback: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
