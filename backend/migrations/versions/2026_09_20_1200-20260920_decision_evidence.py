"""Add structured Decision -> Hypothesis -> Evidence loop tables.

Revision ID: 20260920_decision_evidence
Revises: e7f8a9b0c1d2
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

revision: str = "20260920_decision_evidence"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_hypotheses",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("decision_id", GUID(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("verification_question", sa.Text(), nullable=True),
        sa.Column("validation_action", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_id"], ["destination_decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_hypotheses_user_id",
        "decision_hypotheses",
        ["user_id"],
    )
    op.create_index(
        "ix_decision_hypotheses_decision_id",
        "decision_hypotheses",
        ["decision_id"],
    )
    op.create_index(
        "ix_decision_hypotheses_status",
        "decision_hypotheses",
        ["status"],
    )

    op.create_table(
        "decision_evidence",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("decision_id", GUID(), nullable=False),
        sa.Column("hypothesis_id", GUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="other"),
        sa.Column("reliability", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("stance", sa.String(length=20), nullable=False, server_default="neutral"),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_id"], ["destination_decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["decision_hypotheses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_evidence_user_id",
        "decision_evidence",
        ["user_id"],
    )
    op.create_index(
        "ix_decision_evidence_decision_id",
        "decision_evidence",
        ["decision_id"],
    )
    op.create_index(
        "ix_decision_evidence_hypothesis_id",
        "decision_evidence",
        ["hypothesis_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_decision_evidence_hypothesis_id", table_name="decision_evidence")
    op.drop_index("ix_decision_evidence_decision_id", table_name="decision_evidence")
    op.drop_index("ix_decision_evidence_user_id", table_name="decision_evidence")
    op.drop_table("decision_evidence")

    op.drop_index("ix_decision_hypotheses_status", table_name="decision_hypotheses")
    op.drop_index("ix_decision_hypotheses_decision_id", table_name="decision_hypotheses")
    op.drop_index("ix_decision_hypotheses_user_id", table_name="decision_hypotheses")
    op.drop_table("decision_hypotheses")
