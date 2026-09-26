"""门道卡模型 — 门道信息差的结构化载体（CONTEXT.md 信息差域）。

一条卡 = 一个可交叉验证的门道主张：结论 + 适用条件 + 反例 + 来源链 + 置信度。
数据供给 = AI 定向搜集 + 交叉验证（策展制，非用户生成）；不搬运原文，
卡面只存提炼结论，sources 只存链接与支撑说明。

术语口径（用户 2026-09-26 终审）：
- 官方信息差（official info gap）= 官方已发布但散落的信息，属基建营养，不进本表；
- 门道信息差 = 官方永不发布、散落 UGC 与圈内的知识，本表即其产品化载体；
- 置信度三档：official（官方公示佐证）> multi_source（≥2 独立来源）> single_source（孤证，必标）。
宁可 20 张硬卡不要 200 张水卡；无可信来源的问题不建卡（no_source 如实）。
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin

# category 成员值（A 门道潜规则 / C 圈内消息 / D 内幕实锤）
INTEL_CATEGORY_RULE = "rule"
INTEL_CATEGORY_CIRCLE = "circle"
INTEL_CATEGORY_EVIDENCE = "evidence"

# confidence 三档（CONTEXT.md 门道卡条目）
INTEL_CONFIDENCE_OFFICIAL = "official"
INTEL_CONFIDENCE_MULTI = "multi_source"
INTEL_CONFIDENCE_SINGLE = "single_source"

# status 维护态（B11 维护协议：政策年变→retired，人工抽审可杀卡→killed）
INTEL_STATUS_ACTIVE = "active"
INTEL_STATUS_RETIRED = "retired"
INTEL_STATUS_KILLED = "killed"


class IntelCard(UUIDMixin, TimestampMixin, Base):
    """门道卡 — 全站公共策展内容（无 user_id），track 先行 kaoyan，枚举留扩展。"""

    __tablename__ = "intel_cards"

    track: Mapped[str] = mapped_column(String(20), nullable=False, default="kaoyan", index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    counterexample: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # [{title, url, supports}] — 只存链接与支撑说明，禁止存原文段落
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # D 类实锤客观证据层（如官方公示的复试差额比）：{"metric": ..., "value": ..., "source_url": ...}
    evidence_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 内容时效标注（招生政策年变，过期条件见 docs/门道卡-维护协议）
    as_of: Mapped[str] = mapped_column(String(20), nullable=False, default="2026-09")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=INTEL_STATUS_ACTIVE, index=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
