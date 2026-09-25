"""Decision OS 领域模型（D9 拍板 09-25「开」）。

七实体闭环的第一期垂直切片：destination_decisions 补结构化字段
（question/context/constraints/options/desired_outcome，Q5 拍板=扩展不新建表），
新建五张表：decision_hypotheses / decision_evidence / decision_validation_actions /
decision_outcomes / decision_reflections。

命名拍板（CONTEXT.md）：Evidence 叫 DecisionEvidence（Evidence 已被时间线域占用）；
Action 新建 ValidationAction（三套既有行动系统语义不合，收敛挂账）。
证据一律默认 internal_unverified，任何 externally_verified 必须带 verification_source
（服务层强制，本迁移只管结构）。

downgrade 忠实回滚：五表 drop + 枚举类型 drop + 新增列移除；不改存量数据。

Revision 链：… → b8e4f2a6c9d3 → d3f7a1c5e9b2 → e9c2a7d4f1b3（单头线性）。

Revision ID: e9c2a7d4f1b3
Revises: d3f7a1c5e9b2
Create Date: 2026-09-25 10:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "e9c2a7d4f1b3"
down_revision: Union[str, None] = "d3f7a1c5e9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 枚举类型名与 app/models/decision_os.py 中 Enum(name=...) 严格一致；
# 成员值与成员名相同（本仓枚举约定），迁移内用字面量避免耦合活代码。
_E_IMPORTANCE = sa.Enum("critical", "high", "supporting", name="decision_hypothesis_importance")
_E_HYPO_STATUS = sa.Enum("untested", "supporting", "refuted", "obsolete", name="decision_hypothesis_status")
_E_SOURCE_TYPE = sa.Enum(
    "official", "peer", "media", "internal_db", "user_observed", "ai_generated",
    name="decision_evidence_source_type",
)
_E_RELIABILITY = sa.Enum("high", "medium", "low", name="decision_evidence_reliability")
_E_STANCE = sa.Enum("supporting", "contradicting", "neutral", name="decision_evidence_stance")
_E_VERIFICATION = sa.Enum(
    "internal_unverified", "externally_verified", "contradicted", "stale", "unverifiable",
    name="decision_evidence_verification_status",
)
_E_ACTION_STATUS = sa.Enum("todo", "doing", "done", "skipped", name="decision_action_status")
_E_RESULT_STANCE = sa.Enum(
    "hypothesis_supported", "hypothesis_weakened", "inconclusive", name="decision_action_result_stance"
)
_E_OUTCOME_KIND = sa.Enum(
    "direct", "partial", "unobservable", "counterfactual_unknown", name="decision_outcome_kind"
)
_E_MATCH = sa.Enum("matched", "partial", "missed", "unknown", name="decision_reflection_match_status")

_ALL_ENUMS = (
    _E_IMPORTANCE, _E_HYPO_STATUS, _E_SOURCE_TYPE, _E_RELIABILITY, _E_STANCE,
    _E_VERIFICATION, _E_ACTION_STATUS, _E_RESULT_STANCE, _E_OUTCOME_KIND, _E_MATCH,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    # destination_decisions 补结构化字段（legacy 行全部可空/带默认，不回填）
    op.add_column("destination_decisions", sa.Column("question", sa.String(length=500), nullable=True))
    op.add_column("destination_decisions", sa.Column("context", sa.Text(), nullable=True))
    op.add_column(
        "destination_decisions",
        sa.Column("constraints", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "destination_decisions",
        sa.Column("options", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("destination_decisions", sa.Column("desired_outcome", sa.Text(), nullable=True))

    op.create_table(
        "decision_hypotheses",
        sa.Column("id", GUID(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "decision_id",
            GUID(),
            sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("importance", _E_IMPORTANCE, nullable=False, server_default="high"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", _E_HYPO_STATUS, nullable=False, server_default="untested"),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_hypotheses_user_id", "decision_hypotheses", ["user_id"])
    op.create_index("ix_decision_hypotheses_decision_id", "decision_hypotheses", ["decision_id"])

    op.create_table(
        "decision_evidence",
        sa.Column("id", GUID(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "decision_id",
            GUID(),
            sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "hypothesis_id",
            GUID(),
            sa.ForeignKey("decision_hypotheses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", _E_SOURCE_TYPE, nullable=False, server_default="user_observed"),
        sa.Column("reliability", _E_RELIABILITY, nullable=False, server_default="medium"),
        sa.Column("stance", _E_STANCE, nullable=False, server_default="neutral"),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("verification_status", _E_VERIFICATION, nullable=False, server_default="internal_unverified"),
        sa.Column("verification_source", sa.Text(), nullable=True),
        sa.Column("verified_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_evidence_user_id", "decision_evidence", ["user_id"])
    op.create_index("ix_decision_evidence_decision_id", "decision_evidence", ["decision_id"])
    op.create_index("ix_decision_evidence_hypothesis_id", "decision_evidence", ["hypothesis_id"])

    op.create_table(
        "decision_validation_actions",
        sa.Column("id", GUID(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "decision_id",
            GUID(),
            sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "hypothesis_id",
            GUID(),
            sa.ForeignKey("decision_hypotheses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=True),
        sa.Column("expected_information_gain", sa.Text(), nullable=True),
        sa.Column("status", _E_ACTION_STATUS, nullable=False, server_default="todo"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("result_stance", _E_RESULT_STANCE, nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_validation_actions_user_id", "decision_validation_actions", ["user_id"])
    op.create_index("ix_decision_validation_actions_decision_id", "decision_validation_actions", ["decision_id"])
    op.create_index("ix_decision_validation_actions_hypothesis_id", "decision_validation_actions", ["hypothesis_id"])

    op.create_table(
        "decision_outcomes",
        sa.Column("id", GUID(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "decision_id",
            GUID(),
            sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", _E_OUTCOME_KIND, nullable=False, server_default="direct"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_outcomes_user_id", "decision_outcomes", ["user_id"])
    op.create_index("ix_decision_outcomes_decision_id", "decision_outcomes", ["decision_id"])

    op.create_table(
        "decision_reflections",
        sa.Column("id", GUID(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "decision_id",
            GUID(),
            sa.ForeignKey("destination_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prediction_error", sa.Text(), nullable=True),
        sa.Column("wrong_assumption", sa.Text(), nullable=True),
        sa.Column("omitted_factor", sa.Text(), nullable=True),
        sa.Column("lesson", sa.Text(), nullable=True),
        sa.Column("match_status", _E_MATCH, nullable=False, server_default="unknown"),
        sa.Column("new_principle", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_reflections_user_id", "decision_reflections", ["user_id"])
    op.create_index("ix_decision_reflections_decision_id", "decision_reflections", ["decision_id"])


def downgrade() -> None:
    op.drop_table("decision_reflections")
    op.drop_table("decision_outcomes")
    op.drop_table("decision_validation_actions")
    op.drop_table("decision_evidence")
    op.drop_table("decision_hypotheses")
    op.drop_column("destination_decisions", "desired_outcome")
    op.drop_column("destination_decisions", "options")
    op.drop_column("destination_decisions", "constraints")
    op.drop_column("destination_decisions", "context")
    op.drop_column("destination_decisions", "question")
    for enum_type in _ALL_ENUMS:
        enum_type.drop(op.get_bind(), checkfirst=True)
