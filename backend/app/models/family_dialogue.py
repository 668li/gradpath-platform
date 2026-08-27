"""家庭对话脚手架模型 — 帮大学生和父母沟通职业选择。

调研发现 60% 大学生有家庭期望与个人意愿冲突，父母用旧时代经验指导，
沟通障碍。本模块不是「听父母话」或「反抗父母」，而是「翻译」——
把父母旧时代经验翻译成新时代语境，提供话术模板 + 数据化回应 + 模拟对话练习。

三层结构：理解父母 → 准备弹药 → 实战演练。
"""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class FamilyDialogueSession(UUIDMixin, TimestampMixin, Base):
    """一次家庭对话脚手架会话 — 完整记录「理解 → 准备 → 演练」流程。

    存储父母担忧、用户选择、父母类型、准备的论据、模拟对话记录与状态，
    便于历史回溯与后续基于演练结果做改进建议。
    """

    __tablename__ = "family_dialogue_sessions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 父母主要担心什么，如 "爸妈想让我考公"
    parent_concern: Mapped[str] = mapped_column(String(200), nullable=False)
    # 用户想选什么，如 "我想去互联网公司"
    user_choice: Mapped[str] = mapped_column(String(200), nullable=False)
    # 父母类型: stability_first / prestige_first / practical_worry / supportive
    parent_archetype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 系统生成的「理解父母」分析文本（父母为什么这么想、时代背景、合理部分）
    understanding: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 准备的论据列表，每项含 parent_saying/user_response/data_backing/empathy_note
    prepared_arguments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 沟通技巧列表
    talking_tips: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 模拟对话记录，每项含 role/content
    practice_messages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 会话状态: preparing / practiced / completed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="preparing")
