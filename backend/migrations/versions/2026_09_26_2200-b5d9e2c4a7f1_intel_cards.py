"""门道卡表（批次 B+：门道信息差·考研先行，2026-09-26 五问拍板）。

新建 intel_cards：门道信息差的产品化载体（CONTEXT.md 信息差域）。
全站公共策展内容（无 user_id 列）：结论+适用条件+反例+来源链+三档置信度。
不含任何枚举类型（category/confidence/status 均为 String 列+应用层常量约束），
规避枚举预创建自伤雷（2026-09-25 生产首炸教训）。

downgrade 忠实回滚：drop intel_cards。

Revision 链：… → e9c2a7d4f1b4 → a7f3c8d2e1b9 → b5d9e2c4a7f1（单头线性）。

Revision ID: b5d9e2c4a7f1
Revises: a7f3c8d2e1b9
Create Date: 2026-09-26 22:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID, JSONB

# revision identifiers, used by Alembic.
revision: str = "b5d9e2c4a7f1"
down_revision: Union[str, None] = "a7f3c8d2e1b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intel_cards",
        sa.Column("id", GUID(), primary_key=True, autoincrement=False),
        sa.Column("track", sa.String(20), nullable=False, server_default="kaoyan"),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("question_id", sa.String(10), nullable=False),
        sa.Column("question_text", sa.String(200), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=False),
        sa.Column("conditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("counterexample", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("sources", JSONB(), nullable=False),
        sa.Column("evidence_data", JSONB(), nullable=True),
        sa.Column("as_of", sa.String(20), nullable=False, server_default="2026-09"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_intel_cards_track", "intel_cards", ["track"])
    op.create_index("ix_intel_cards_category", "intel_cards", ["category"])
    op.create_index("ix_intel_cards_question_id", "intel_cards", ["question_id"])
    op.create_index("ix_intel_cards_confidence", "intel_cards", ["confidence"])
    op.create_index("ix_intel_cards_status", "intel_cards", ["status"])


def downgrade() -> None:
    op.drop_index("ix_intel_cards_status", table_name="intel_cards")
    op.drop_index("ix_intel_cards_confidence", table_name="intel_cards")
    op.drop_index("ix_intel_cards_question_id", table_name="intel_cards")
    op.drop_index("ix_intel_cards_category", table_name="intel_cards")
    op.drop_index("ix_intel_cards_track", table_name="intel_cards")
    op.drop_table("intel_cards")
