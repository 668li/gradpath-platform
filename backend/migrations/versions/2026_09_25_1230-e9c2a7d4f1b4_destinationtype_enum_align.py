"""destinationtype 枚举存量漂移修复：补 postgrad / phd（Decision OS 冒烟发现）。

initial_schema 里两张表先后以同名 destinationtype 建枚举，先建的定义
{employment, further_study, civil_service, abroad, startup, gap_year} 赢得类型名，
destination_decisions.destination_type 实际落在这一份上——模型的 postgrad / phd
自始插不进生产库（被 D8①"决策创建入口不可达"掩盖，表 0 行）。09-25 Decision OS
部署冒烟实测撞出（invalid input value for enum destinationtype: "postgrad"）。

生产已于 09-25 直接 ALTER 补值解锁冒烟；本迁移把同一修复写进仓库真相，
保证新环境从迁移链建库后枚举与模型一致。PG16 下 ADD VALUE IF NOT EXISTS
幂等，重复部署/已手工补值的环境均为 no-op。further_study 为历史标签保留
（模型已不再产出该值，无删除枚举值的安全手段，留作兼容）。

Revision 链：… → d3f7a1c5e9b2 → e9c2a7d4f1b3 → e9c2a7d4f1b4（单头线性）。

Revision ID: e9c2a7d4f1b4
Revises: e9c2a7d4f1b3
Create Date: 2026-09-25 12:30:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9c2a7d4f1b4"
down_revision: Union[str, None] = "e9c2a7d4f1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE destinationtype ADD VALUE IF NOT EXISTS 'postgrad'")
    op.execute("ALTER TYPE destinationtype ADD VALUE IF NOT EXISTS 'phd'")


def downgrade() -> None:
    # PostgreSQL 不支持从枚举类型安全移除值；补值保持（加法兼容），诚实 no-op。
    pass
