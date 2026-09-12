"""考公流程时间线伴随 MVP（feature 001）— 六表建链。

信息差伴随层脊柱：考次×12环节（诚实日期三态）、证据链行（OFFICIAL 唯一合法来源）、
订阅、节点回传、提醒日志（unique(user,node,kind) 幂等硬闸）。
down_revision 实证生产 alembic current=c8d4e6f2a9b1（09-12 topology 双实锤），禁幻影 stamp。

Revision ID: f1a3b5c7d9e2
Revises: c8d4e6f2a9b1
Create Date: 2026-09-12 18:00:00.000000+00:00

Revision 链：... → b5d9e2a4c7f8 → c8d4e6f2a9b1 → f1a3b5c7d9e2（单头线性）。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "f1a3b5c7d9e2"
down_revision: Union[str, None] = "c8d4e6f2a9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "t_timeline_evidence",
        sa.Column("id", GUID(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("fetch", "manual_paste", name="evidencechannel"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha", sa.String(length=64), nullable=False),
        sa.Column("matched_excerpt", sa.Text(), nullable=False),
        sa.Column("pasted_text", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_t_timeline_evidence")),
    )
    op.create_index(op.f("ix_t_timeline_evidence_source_url"), "t_timeline_evidence", ["source_url"])

    op.create_table(
        "t_exam",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("track", sa.String(length=30), nullable=False, server_default="guokao"),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("official_home_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="upcoming"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_t_exam")),
        sa.UniqueConstraint("code", name=op.f("uq_t_exam_code")),
    )
    op.create_index(op.f("ix_t_exam_code"), "t_exam", ["code"])

    op.create_table(
        "t_exam_node",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("exam_id", GUID(), nullable=False),
        sa.Column(
            "stage_key",
            sa.Enum(
                "announce",
                "registration",
                "payment",
                "admission_ticket",
                "written",
                "score",
                "adjustment",
                "interview",
                "medical",
                "political",
                "publicity",
                "hire",
                name="nodestage",
            ),
            nullable=False,
        ),
        sa.Column("node_seq", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column(
            "date_status",
            sa.Enum("OFFICIAL", "PREDICTED", "UNKNOWN", name="datestatus"),
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("predict_basis", sa.String(length=200), nullable=True),
        sa.Column("official_entry_url", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_id", GUID(), nullable=True),
        sa.Column("materials", JSONB(), nullable=False, server_default="[]"),
        sa.Column("action_guide", sa.Text(), nullable=False, server_default=""),
        sa.Column("announced_via_announce_id", GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["t_exam.id"], name=op.f("fk_t_exam_node_exam"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["t_timeline_evidence.id"], name=op.f("fk_t_exam_node_evidence")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_t_exam_node")),
        sa.UniqueConstraint("exam_id", "stage_key", name=op.f("uq_exam_node_stage")),
    )
    op.create_index(op.f("ix_t_exam_node_exam_id"), "t_exam_node", ["exam_id"])

    op.create_table(
        "t_exam_subscription",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("exam_id", GUID(), nullable=False),
        sa.Column("notify_channels", JSONB(), nullable=False, server_default='["inapp","serverchan"]'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_t_exam_subscription_user"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["t_exam.id"], name=op.f("fk_t_exam_subscription_exam"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_t_exam_subscription")),
        sa.UniqueConstraint("user_id", "exam_id", name=op.f("uq_exam_subscription_user_exam")),
    )
    op.create_index(op.f("ix_t_exam_subscription_user_id"), "t_exam_subscription", ["user_id"])
    op.create_index(op.f("ix_t_exam_subscription_exam_id"), "t_exam_subscription", ["exam_id"])

    op.create_table(
        "t_exam_node_feedback",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("subscription_id", GUID(), nullable=False),
        sa.Column("node_id", GUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("done", "uncertain", "skipped", name="nodefeedbackstatus"),
            nullable=False,
        ),
        sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["t_exam_subscription.id"],
            name=op.f("fk_t_exam_node_feedback_sub"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["t_exam_node.id"], name=op.f("fk_t_exam_node_feedback_node"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_t_exam_node_feedback")),
        sa.UniqueConstraint("subscription_id", "node_id", name=op.f("uq_node_feedback_sub_node")),
    )
    op.create_index(op.f("ix_t_exam_node_feedback_subscription_id"), "t_exam_node_feedback", ["subscription_id"])
    op.create_index(op.f("ix_t_exam_node_feedback_node_id"), "t_exam_node_feedback", ["node_id"])

    op.create_table(
        "t_timeline_reminder_log",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("node_id", GUID(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("heads_up", "opening", "deadline_t1", "dayof", "followup", name="reminderkind"),
            nullable=False,
        ),
        sa.Column(
            "tone", sa.Enum("assertive", "tentative", name="remindertone"), nullable=False
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False, server_default="inapp"),
        sa.Column("notification_id", GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_t_timeline_reminder_log_user"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["t_exam_node.id"], name=op.f("fk_t_timeline_reminder_log_node"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_t_timeline_reminder_log")),
        sa.UniqueConstraint("user_id", "node_id", "kind", name=op.f("uq_reminder_user_node_kind")),
    )
    op.create_index(op.f("ix_t_timeline_reminder_log_user_id"), "t_timeline_reminder_log", ["user_id"])
    op.create_index(op.f("ix_t_timeline_reminder_log_node_id"), "t_timeline_reminder_log", ["node_id"])


def downgrade() -> None:
    for table in (
        "t_timeline_reminder_log",
        "t_exam_node_feedback",
        "t_exam_subscription",
        "t_exam_node",
        "t_exam",
        "t_timeline_evidence",
    ):
        op.drop_table(table)
    # PG 原生枚举类型不随表消失，显式清理保证升降级演练可往返。
    # 固定 SQL 字符串列表（无动态拼接，对齐安全扫描约束）。
    if op.get_bind().dialect.name == "postgresql":
        op.execute('DROP TYPE IF EXISTS "reminderkind"')
        op.execute('DROP TYPE IF EXISTS "remindertone"')
        op.execute('DROP TYPE IF EXISTS "nodefeedbackstatus"')
        op.execute('DROP TYPE IF EXISTS "datestatus"')
        op.execute('DROP TYPE IF EXISTS "nodestage"')
        op.execute('DROP TYPE IF EXISTS "evidencechannel"')
