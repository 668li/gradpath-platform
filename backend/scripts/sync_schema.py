#!/usr/bin/env python
"""Schema 自动同步工具 — 检测并修复 SQLAlchemy 模型与数据库的列不一致。

背景:
    项目反复出现"模型定义了列但数据库表里没建"的情况
    （如 notifications.archived, streak_records.is_rest_day），
    导致 API 触发 500。本工具自动检测并安全地 ADD COLUMN 修复。

用法:
    python scripts/sync_schema.py --check       # 仅检测，不一致返回 1（CI/CD 友好）
    python scripts/sync_schema.py --generate    # 输出 ALTER TABLE SQL 到 stdout，不执行
    python scripts/sync_schema.py --apply       # 执行 ALTER TABLE ADD COLUMN
    python scripts/sync_schema.py --dry-run     # 显示会执行什么，但不实际执行
    python scripts/sync_schema.py               # 默认等同 --check

Docker 调用:
    docker exec gradpath-backend-1 python /app/scripts/sync_schema.py --check

安全策略:
    1. 只做 ADD COLUMN，永远不做 DROP COLUMN 或 ALTER COLUMN（避免数据丢失）
    2. 每张表使用独立 session，单个 ALTER 失败回滚后不影响后续表
    3. server_default 仅在模型显式声明时写入 SQL，不臆造默认值
    4. 默认行为是 --check，不修改任何东西
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# 允许从 backend/ 或容器内 /app 直接运行，也允许从项目根目录调用
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_HERE)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402


# ---------------------------------------------------------------------------
# 模型加载
# ---------------------------------------------------------------------------
def load_all_models() -> None:
    """强制加载 app.models 下所有模块，确保 Base.metadata 注册所有表。

    app.models.__init__ 已经 import 了大部分模型，但用 pkgutil 兜底，
    避免新增模型文件后忘记在 __init__.py 注册导致漏检。
    """
    import importlib
    import pkgutil

    import app.models

    for _finder, name, _is_pkg in pkgutil.iter_modules(app.models.__path__):
        try:
            importlib.import_module(f"app.models.{name}")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: 跳过 app.models.{name}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 检测
# ---------------------------------------------------------------------------
def find_missing_columns() -> dict[str, dict[str, Any]]:
    """返回 {table_name: {col_name: Column, ...}, ...}。

    只检测"模型有、数据库没有"的列，不反向检测多余列（安全策略：只增不删）。
    只对比数据库和模型都存在的表，避免对未建表的模型误报。
    """
    load_all_models()
    insp = inspect(engine)
    db_tables = set(insp.get_table_names())
    model_tables = set(Base.metadata.tables.keys())

    result: dict[str, dict[str, Any]] = {}
    for table_name in sorted(db_tables & model_tables):
        db_cols = {c["name"] for c in insp.get_columns(table_name)}
        model_cols = Base.metadata.tables[table_name].columns
        missing = {name: col for name, col in model_cols.items() if name not in db_cols}
        if missing:
            result[table_name] = missing
    return result


# ---------------------------------------------------------------------------
# SQL 生成
# ---------------------------------------------------------------------------
def _get_dialect() -> postgresql.dialect:
    """返回 PostgreSQL dialect，用于编译类型和 server_default。

    即使生产环境用 PostgreSQL，本地测试用 SQLite 时也按 PostgreSQL 方言生成 SQL，
    因为 ALTER TABLE 实际只在生产 PostgreSQL 上执行（通过 docker exec）。
    """
    return postgresql.dialect()


def compile_type(col_obj: Any) -> str:
    """把 Column.type 编译为 PostgreSQL SQL 类型字符串。

    覆盖项目中所有类型：
    - Boolean / Integer / Float / String(N) / Text
    - DateTime(timezone=True) / Date
    - Enum(SomePyEnum) → 自动转为 VARCHAR(N) 或 postgresql.ENUM
    - JSONB (app.models.base.JSONB, TypeDecorator) → 编译为 jsonb
    - GUID  (app.models.base.GUID,  TypeDecorator) → 编译为 uuid
    - JSON  (sqlalchemy.JSON)                     → 编译为 json
    """
    try:
        return col_obj.type.compile(dialect=_get_dialect())
    except Exception as exc:  # noqa: BLE001
        return f"<type compile failed: {exc}>"


def compile_server_default(col_obj: Any) -> str | None:
    """提取 server_default 的 SQL 文本。

    覆盖项目所有用法:
    - server_default=func.now()         → "now()"
    - server_default=text("false")      → "false"
    - server_default=text("0")          → "0"
    - server_default="'some literal'"   → "'some literal'"

    若模型未声明 server_default，返回 None（ADD COLUMN 不带 DEFAULT，
    PostgreSQL 会用类型默认值，NOT NULL 列需在应用层保证 INSERT 时给值）。
    """
    sd = col_obj.server_default
    if sd is None:
        return None

    dialect = _get_dialect()
    # DefaultClause 包装：.arg 才是真正的表达式
    arg = getattr(sd, "arg", sd)

    # SQLAlchemy 表达式对象（func.now()、text()、ColumnElement 等）
    if hasattr(arg, "compile"):
        try:
            return str(
                arg.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
            ).strip()
        except Exception as exc:  # noqa: BLE001
            return f"<server_default compile failed: {exc}>"

    # Python 端字面量（少见，但兼容 server_default=False / 0 / "x"）
    if isinstance(arg, bool):
        return "true" if arg else "false"
    if isinstance(arg, (int, float)):
        return str(arg)
    if isinstance(arg, str):
        # 已是 SQL 文本（如 "false"、"0"、"'literal'"），原样返回
        return arg
    return str(arg)


def generate_alter_sql(table_name: str, col_name: str, col_obj: Any) -> str:
    """生成单条 ALTER TABLE ADD COLUMN 语句（PostgreSQL 方言，带分号）。"""
    parts: list[str] = [f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}"']
    parts.append(compile_type(col_obj))

    if not col_obj.nullable:
        parts.append("NOT NULL")

    sd_sql = compile_server_default(col_obj)
    if sd_sql:
        parts.append(f"DEFAULT {sd_sql}")

    if col_obj.comment:
        # PostgreSQL 单引号转义
        escaped = col_obj.comment.replace("'", "''")
        parts.append(f"COMMENT '{escaped}'")

    return " ".join(parts) + ";"


# ---------------------------------------------------------------------------
# 应用迁移
# ---------------------------------------------------------------------------
def apply_migration(table_name: str, col_name: str, col_obj: Any) -> tuple[bool, str]:
    """执行 ALTER TABLE ADD COLUMN。

    使用独立 session，失败时回滚并返回错误信息，不影响后续表迁移。
    返回 (是否成功, SQL 或错误信息)。
    """
    sql = generate_alter_sql(table_name, col_name, col_obj)
    db = SessionLocal()
    try:
        db.execute(text(sql))
        db.commit()
        return True, sql
    except SQLAlchemyError as exc:
        db.rollback()
        return False, f"{sql}\n  ERROR: {exc}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 报告格式化
# ---------------------------------------------------------------------------
def format_missing(missing: dict[str, dict[str, Any]]) -> str:
    """格式化缺失列报告（用于 --check / --dry-run 输出）。"""
    lines: list[str] = []
    for table_name, cols in missing.items():
        lines.append(f"  [{table_name}] 缺失 {len(cols)} 列:")
        for col_name, col_obj in cols.items():
            type_sql = compile_type(col_obj)
            sd = compile_server_default(col_obj)
            nullable = "NO" if not col_obj.nullable else "YES"
            line = (
                f"    - {col_name}: {type_sql}"
                f" | nullable={nullable}"
                f"{f' | default={sd}' if sd else ''}"
                f"{f' | comment={col_obj.comment!r}' if col_obj.comment else ''}"
            )
            lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Schema 自动同步工具 — 检测并修复 SQLAlchemy 模型与数据库的列不一致",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "安全策略: 只做 ADD COLUMN，永远不做 DROP/ALTER COLUMN。\n"
            "默认行为: --check（仅检测，不修改）。"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="仅检测不一致（CI/CD 友好，退出码 0/1）"
    )
    mode.add_argument(
        "--generate", action="store_true", help="生成 ALTER TABLE SQL，输出到 stdout，不执行"
    )
    mode.add_argument(
        "--apply", action="store_true", help="执行 ALTER TABLE ADD COLUMN（每表独立事务）"
    )
    mode.add_argument(
        "--dry-run", action="store_true", help="显示会执行什么 SQL，但不实际执行"
    )
    args = parser.parse_args()

    # 默认行为：--check
    if not any([args.check, args.generate, args.apply, args.dry_run]):
        args.check = True

    # 检测
    try:
        missing = find_missing_columns()
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: 检测失败: {exc}", file=sys.stderr)
        return 2

    if not missing:
        print("✅ Schema 一致：所有模型列都存在于数据库中。")
        return 0

    total = sum(len(cols) for cols in missing.values())
    print(f"⚠️  发现 {total} 个缺失列，分布在 {len(missing)} 张表：\n")
    print(format_missing(missing))

    if args.check:
        print("\n提示: 运行 --dry-run 查看将执行的 SQL，或 --apply 执行修复。")
        return 1

    if args.generate:
        print("\n-- 生成的 ALTER TABLE SQL (PostgreSQL):\n")
        for table_name, cols in missing.items():
            for col_name, col_obj in cols.items():
                print(generate_alter_sql(table_name, col_name, col_obj))
        return 0

    if args.dry_run:
        print("\n-- Dry-run: 以下 SQL 会被执行 (--apply):\n")
        for table_name, cols in missing.items():
            for col_name, col_obj in cols.items():
                print("[DRY-RUN]", generate_alter_sql(table_name, col_name, col_obj))
        return 0

    if args.apply:
        print("\n-- 开始执行 ALTER TABLE ADD COLUMN...\n")
        success = failed = 0
        for table_name, cols in missing.items():
            for col_name, col_obj in cols.items():
                ok, info = apply_migration(table_name, col_name, col_obj)
                if ok:
                    success += 1
                    print(f"  ✅ {info}")
                else:
                    failed += 1
                    print(f"  ❌ {info}")
        print(f"\n完成: 成功 {success} 个，失败 {failed} 个。")
        return 0 if failed == 0 else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
