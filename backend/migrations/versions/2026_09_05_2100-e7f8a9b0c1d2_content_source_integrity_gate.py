"""内容真实性门禁：机器供给的内容必须带可溯源 source_url。

2026-09-05 社区/供给链假数据连环整改的收官闸（用户拍板"我不要出现这个情况了"）：
mentors 1730 条合成扩量、43 条假考公情报、581 假进面线的共同根因是
"入库无真实性门禁"——任何脚本可写无来源内容直达用户。本迁移用数据库层
CHECK 约束把规则焊死在库里，绕过一切应用层代码的写入也会被拒绝：

- mentors / market_data / t_external_research_item / grad_yanzhao_programs：
  纯机器供给表，source_url 必填（生产存量已实证 100% 满足，mentors 已清零）
- experience_posts：用户自述内容豁免（source_platform 为空或 'user'），
  其余来源必须带 source_url——防止爬虫导入器再灌无溯源内容

约束名统一前缀 ck_source_gate_，回滚即 DROP。

Revision ID: e7f8a9b0c1d2
Revises: d5f2a8e1c3b7
Create Date: 2026-09-05 21:05
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e7f8a9b0c1d2"
down_revision = "d5f2a8e1c3b7"
branch_labels = None
depends_on = None

# (table, constraint_name, check_sql)
GATES = [
    (
        "mentors",
        "ck_source_gate_mentors",
        "source_url IS NOT NULL AND source_url <> ''",
    ),
    (
        "market_data",
        "ck_source_gate_market_data",
        "source_url IS NOT NULL AND source_url <> ''",
    ),
    (
        "t_external_research_item",
        "ck_source_gate_t_external_research_item",
        "source_url IS NOT NULL AND source_url <> ''",
    ),
    (
        "grad_yanzhao_programs",
        "ck_source_gate_grad_yanzhao_programs",
        "source_url IS NOT NULL AND source_url <> ''",
    ),
    (
        "experience_posts",
        "ck_source_gate_experience_posts",
        "(source_platform IS NULL OR source_platform = 'user' OR (source_url IS NOT NULL AND source_url <> ''))",
    ),
]


def upgrade() -> None:
    for table, name, check in GATES:
        op.create_check_constraint(name, table, check)


def downgrade() -> None:
    for table, name, _ in GATES:
        op.drop_constraint(name, table, type_="check")
