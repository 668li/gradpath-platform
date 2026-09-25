import enum
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class PeriodType(str, enum.Enum):
    annual = "annual"
    quarterly = "quarterly"
    project = "project"
    custom = "custom"


class Retrospective(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "retrospectives"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    achievements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    challenges: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    satisfaction: Mapped[int] = mapped_column(Integer, nullable=False)


class PrincipleStatus(str, enum.Enum):
    """原则生命周期状态机（KPT Try 复审 + 联想"一两次复盘别急着定规律"）。

    draft: 草稿（首次提炼，未经复验）
    verified: 已验证（下次遇到同类情境用上且有效 ≥1 次）
    invalid: 已失效（复验无效或用户主动废弃）
    """

    draft = "draft"
    verified = "verified"
    invalid = "invalid"


class RetroPrinciple(UUIDMixin, TimestampMixin, Base):
    """复盘原则库 — 用户经验沉淀的唯一真相源。

    条目三要素（Dalio 原则写法 / NASA LLIS 条目规范 / 错题本"错因归类"共识）：
    触发条件（if）+ 行动指令（then）+ 来源案例（source_retro_id + snapshot）。
    每条带验证状态机与复审时间：原则是活的，复验无效要降级或修订，不许躺尸。

    刻意不做 user_memory_facts 双写（对抗审查裁决：双真相源必然漂移）；
    chat 注入直查本表（chat_service【个人原则】段）。
    """

    __tablename__ = "retro_principles"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 触发条件："下次遇到____情况时"，≤120 字，必须具体到情境
    trigger_scene: Mapped[str] = mapped_column(String(200), nullable=False)
    # 行动指令："我应该____"，≤200 字，可执行（空话闸在 service 层拦截）
    action: Mapped[str] = mapped_column(String(400), nullable=False)
    # 原理一句话（可选）："因为____"
    rationale: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 场景标签：[模考崩盘][择校纠结][面试复盘]…，用于情境匹配
    scene_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    status: Mapped[PrincipleStatus] = mapped_column(
        Enum(PrincipleStatus), nullable=False, default=PrincipleStatus.draft, index=True
    )
    verify_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 来源案例（三要素之一：原则必须能下钻到它诞生的那次复盘）
    source_retro_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("retrospectives.id", ondelete="SET NULL"), nullable=True
    )
    source_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    next_review_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class RetroActionStatus(str, enum.Enum):
    """Try 行动卡状态（KPT：Try 是实验不是政策，到期必须复审）。

    pending: 待验证（复盘产出时的初始态）
    effective: 复审裁决=有效（可升级为原则）
    ineffective: 复审裁决=无效（记录原因，别再试）
    not_met: 还没遇到触发场景（顺延复审日期）
    """

    pending = "pending"
    effective = "effective"
    ineffective = "ineffective"
    not_met = "not_met"


class RetroAction(UUIDMixin, TimestampMixin, Base):
    """Try 行动卡 — 复盘的"下次再发生怎么办"落地件。

    每次复盘强制输出 ≤3 条（KPT 铁律：六条 Try 意味着一条也得不到关注），
    每条带触发场景 + 复审日期（默认 +14 天）。下次新建复盘开场先复审到期卡
    （M&M 会议开场核对上次行动项 / Edgewonk 周复盘最后一步同构）。
    """

    __tablename__ = "retro_actions"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retro_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("retrospectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 做什么："我应该____"（可执行动作）
    content: Mapped[str] = mapped_column(String(400), nullable=False)
    # 什么情境下用："当____时"
    trigger_scene: Mapped[str] = mapped_column(String(200), nullable=False)

    status: Mapped[RetroActionStatus] = mapped_column(
        Enum(RetroActionStatus), nullable=False, default=RetroActionStatus.pending, index=True
    )
    review_due_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 复审 effective 后升级成的原则（闭环：行动验证有效 → 沉淀为原则）
    principle_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("retro_principles.id", ondelete="SET NULL"), nullable=True
    )
