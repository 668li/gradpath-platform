"""添加查询性能索引

Revision ID: c4d2e6f8a1b3
Revises: 9c43ddf069ce
Create Date: 2026-07-23 00:00:00.000000+00:00

为常用查询字段添加单列索引，优化看板与列表查询性能：
- destination_decisions: decision_date, destination_type, status
- career_events: event_type
- retrospectives: period_end
- skill_nodes: parent_id
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d2e6f8a1b3"
down_revision: Union[str, None] = "9c43ddf069ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # destination_decisions
    op.create_index(
        op.f("ix_destination_decisions_decision_date"),
        "destination_decisions",
        ["decision_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_destination_decisions_destination_type"),
        "destination_decisions",
        ["destination_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_destination_decisions_status"),
        "destination_decisions",
        ["status"],
        unique=False,
    )
    # career_events
    op.create_index(
        op.f("ix_career_events_event_type"),
        "career_events",
        ["event_type"],
        unique=False,
    )
    # retrospectives
    op.create_index(
        op.f("ix_retrospectives_period_end"),
        "retrospectives",
        ["period_end"],
        unique=False,
    )
    # skill_nodes
    op.create_index(
        op.f("ix_skill_nodes_parent_id"),
        "skill_nodes",
        ["parent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_skill_nodes_parent_id"), table_name="skill_nodes")
    op.drop_index(op.f("ix_retrospectives_period_end"), table_name="retrospectives")
    op.drop_index(op.f("ix_career_events_event_type"), table_name="career_events")
    op.drop_index(op.f("ix_destination_decisions_status"), table_name="destination_decisions")
    op.drop_index(op.f("ix_destination_decisions_destination_type"), table_name="destination_decisions")
    op.drop_index(op.f("ix_destination_decisions_decision_date"), table_name="destination_decisions")
