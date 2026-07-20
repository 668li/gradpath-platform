"""Alembic 迁移环境配置。

从 app.config.settings 读取数据库 URL（而非 alembic.ini 中的硬编码值），
并导入所有模型以确保 autogenerate 能检测到表结构变更。
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 将 backend/ 加入 sys.path，确保能导入 app.*
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 导入配置与 Base
from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

# 导入所有模型，确保 Base.metadata 注册全部表
import app.models  # noqa: F401, E402

# Alembic 配置对象
config = context.config

# 从应用配置覆盖 sqlalchemy.url
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标 metadata — autogenerate 比对依据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本而不连接数据库。

    适用于 CI/CD 或无数据库连接的环境。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # SQLite 支持 ALTER 批量模式
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
