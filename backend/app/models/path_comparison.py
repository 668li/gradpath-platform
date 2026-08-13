"""多路径 What-If 对比模型 — 量化对比多条职业路径。

竞品调研发现「人生星途」的 What-If 沙盒被评为「创新度高」，可对比
继续深造 / 转行 / 跳槽大厂 / 创业等多场景。本模块是其简化版：让用户
选 2-3 条路径，量化对比收入 / 风险 / 成长性 / 时间成本 / 匹配度。
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class PathComparison(UUIDMixin, TimestampMixin, Base):
    """一次多路径 What-If 对比记录。

    存储用户选择的 2-3 条路径及对应的量化对比结果，便于历史回溯与
    后续基于对比结果做深度决策分析。
    """

    __tablename__ = "path_comparisons"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 用户选择的路径列表，每项形如 {"path_type": "kaoyan", "target_role": "后端开发"}
    paths: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 对比结果，含每条路径的量化指标和综合建议
    comparison_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # 可选的用户上下文摘要（如 holland 代码），用于匹配度复算
    user_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    # 综合建议自然语言文本（冗余字段，便于直接展示）
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
