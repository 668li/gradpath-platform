"""gwy_position.grassroots_exp_req 拓宽至 100

国考职位表中"基层工作经历要求"列存在合法长文本（四项目人员完整分类描述，
实测最长 68 字符），String(50) 会在导入/迁移时截断或拒收真实数据。

Revision ID: b3e8c7a1f602
Revises: 471e68459202
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3e8c7a1f602"
down_revision = "471e68459202"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("gwy_position") as batch_op:
        batch_op.alter_column(
            "grassroots_exp_req",
            existing_type=sa.String(length=50),
            type_=sa.String(length=100),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("gwy_position") as batch_op:
        batch_op.alter_column(
            "grassroots_exp_req",
            existing_type=sa.String(length=100),
            type_=sa.String(length=50),
            existing_nullable=True,
        )
