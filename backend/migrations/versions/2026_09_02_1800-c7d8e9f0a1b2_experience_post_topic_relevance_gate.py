"""experience post topic relevance gate (S1)

Revision ID: c7d8e9f0a1b2
Revises: f4a7b8c9d1e2
Create Date: 2026-09-02 18:00:00.000000+00:00

主题相关度门禁（S1 / 三角洲游戏视频事故的根治）：experience_posts 新增
is_off_topic / topic_reason / topic_domain 三列，用于标记被判定为离题的内容。

- is_off_topic True = 命中离题黑名单或无领域信号，feed 硬过滤不展示，
  但保留 status=approved 与溯源（管理员可复核，可恢复）。
- topic_reason：判定说明（命中离题词 / 无领域信号）。
- topic_domain：归属领域（kaoyan/gongkao/certificate/employment/study）。

按仓库惯例可空（NOT NULL 需 server_default 会与模型 Python default 形成
alembic 漂移），模型端 default 保证新插入行有值，NULL=旧数据未检测。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'f4a7b8c9d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('experience_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_off_topic', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('topic_reason', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('topic_domain', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('experience_posts', schema=None) as batch_op:
        batch_op.drop_column('topic_domain')
        batch_op.drop_column('topic_reason')
        batch_op.drop_column('is_off_topic')