"""Link MicroActionPlan/Task to Decision OS.

Revision ID: 20260920_action_links
Revises: 20260920_decision_evidence
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

revision: str = "20260920_action_links"
down_revision: Union[str, None] = "20260920_decision_evidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("micro_action_plans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("decision_id", GUID(), nullable=True))
        batch_op.create_index("ix_micro_action_plans_decision_id", ["decision_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_micro_action_plans_decision_id",
            "destination_decisions",
            ["decision_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("micro_action_tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hypothesis_id", GUID(), nullable=True))
        batch_op.create_index("ix_micro_action_tasks_hypothesis_id", ["hypothesis_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_micro_action_tasks_hypothesis_id",
            "decision_hypotheses",
            ["hypothesis_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("micro_action_tasks", schema=None) as batch_op:
        batch_op.drop_constraint("fk_micro_action_tasks_hypothesis_id", type_="foreignkey")
        batch_op.drop_index("ix_micro_action_tasks_hypothesis_id")
        batch_op.drop_column("hypothesis_id")

    with op.batch_alter_table("micro_action_plans", schema=None) as batch_op:
        batch_op.drop_constraint("fk_micro_action_plans_decision_id", type_="foreignkey")
        batch_op.drop_index("ix_micro_action_plans_decision_id")
        batch_op.drop_column("decision_id")
