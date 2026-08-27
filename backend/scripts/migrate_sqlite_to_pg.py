"""SQLite → PostgreSQL 全量数据迁移（上线一次性迁移工具，纯 pandas/Core API 实现）。

用法（在 backend/ 目录下）:

    py -3.13 scripts/migrate_sqlite_to_pg.py --drop-existing [--stamp-head]
    docker exec gradpath-pg psql -U gradpath -d gradpath \
        -f /docker-entrypoint-initdb.d/align_pg_sequences.sql   # 序列对齐

端点配置（均有安全默认值 = 本机演练库；服务器上用环境变量覆盖）:

    MIGRATE_SRC   源 sqlite 文件路径（默认 ./gradpath.db）
    MIGRATE_TGT   目标 postgresql URL（默认本地 5433 演练容器）

设计要点:
  1. 目标库 schema 由 ORM 模型（app.database.Base.metadata）生成 —— 在
     PostgreSQL 上整型主键自动渲染为 SERIAL，天然避免自增序列缺失问题。
  2. 数据搬运全程 pandas read_sql_table / to_sql 与 SQLAlchemy Core 表达式，
     无任何手写 SQL 字符串。
  3. SERIAL 序列推进由配套的 align_pg_sequences.sql 在数据库内部完成
     （information_schema 目录驱动 + EXECUTE format，见同目录文件）。
  4. 对账：逐表行数 源→目标 必须一致否则非零退出；附孤儿行抽查报告。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import sqlalchemy as sa

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 迁移上下文只需要模型元数据；给 settings 一个占位 key 以通过启动校验
os.environ.setdefault("SECRET_KEY", "offline-migration-no-secrets-needed-key")
os.environ.setdefault("ENVIRONMENT", "development")

_INTERNAL_TABLES_PREFIX = ("sqlite_",)
_INTERNAL_TABLES = {"alembic_version"}

# 默认端点仅指向本机演练容器；生产迁移必须用环境变量覆盖
_DEFAULT_SRC = "./gradpath.db"
_DEFAULT_TGT = "postgresql://gradpath:rehearsal123@127.0.0.1:5433/gradpath"

_SRC_RE = re.compile(r"^[\w\-.\\/ :]{1,260}\.db$")
_TGT_RE = re.compile(
    r"^postgresql(\+psycopg2)?://[\w]{1,64}:[^\s@:/]{1,128}@[A-Za-z0-9_.:\[\]-]{1,253}"
    r":[0-9]{1,5}/[A-Za-z0-9_]{1,63}$"
)


def _fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(1)


def load_endpoints() -> tuple[Path, str]:
    src_raw = os.environ.get("MIGRATE_SRC", "").strip() or _DEFAULT_SRC
    tgt_raw = os.environ.get("MIGRATE_TGT", "").strip() or _DEFAULT_TGT
    p = Path(src_raw)
    if not _SRC_RE.fullmatch(str(p)) or not p.is_file():
        _fail(f"MIGRATE_SRC 未通过校验或文件不存在: {p}")
    if not _TGT_RE.fullmatch(tgt_raw):
        _fail(f"MIGRATE_TGT 未通过校验: {tgt_raw[:64]}...")
    return p.resolve(), tgt_raw


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SQLite → PostgreSQL 数据迁移")
    p.add_argument("--drop-existing", action="store_true",
                   help="拷贝前清空目标库所有业务表（重建 schema）")
    p.add_argument("--batch-size", type=int, default=400)
    p.add_argument("--stamp-head", action="store_true",
                   help="迁移后把目标库迁移版本对齐到 head")
    return p.parse_args()


def _scalar_default(col: sa.Column):
    """取客户端或服务端标量默认值；无则返回 None（uuid4/now 等 callable 排除）。"""
    dflt = col.default
    if dflt is not None and getattr(dflt, "is_scalar", False) \
            and getattr(dflt, "arg", None) is not None:
        return dflt.arg
    srv = col.server_default
    if srv is not None and hasattr(srv, "arg"):
        arg = srv.arg
        if isinstance(arg, sa.sql.elements.TextClause):
            return None
        if isinstance(arg, sa.sql.functions.FunctionElement):
            return None
        return arg
    return None


def _unique_col_groups(tgt_meta: sa.Table) -> list[list[str]]:
    """收集表上全部唯一性约束的列组合（UniqueConstraint 与唯一索引两类）。"""
    groups: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for cons in tgt_meta.constraints:
        cols = [c.name for c in getattr(cons, "columns", [])]
        if isinstance(cons, sa.UniqueConstraint) and cols:
            key = tuple(cols)
            if key not in seen:
                seen.add(key)
                groups.append(cols)
    for idx in tgt_meta.indexes:
        cols = [c.name for c in idx.columns]
        if idx.unique and cols:
            key = tuple(cols)
            if key not in seen:
                seen.add(key)
                groups.append(cols)
    return groups


def _safe_null(v) -> bool:
    """对任意 Python 值安全判空（dict/list/ndarray 直接排除，NaN 用自反比较）。"""
    if v is None:
        return True
    if isinstance(v, (dict, list)):
        return False
    return isinstance(v, float) and v != v


def coerce_frame(frame: pd.DataFrame, src_meta: sa.Table,
                 kept_names: list[str], tgt_meta: sa.Table) \
        -> tuple[pd.DataFrame, int]:
    """列交集过滤 + 类型适配。返回 (帧, 缺失非空字段按默认回填的单元格数)。

    转换规则：
      - dict/list 单元格 → json.dumps 文本（psycopg2 无法适配容器类型，
        PG 端 json/jsonb 列会把合法 JSON 文本直接收下）
      - BOOLEAN 声明列的 0/1 → bool
      - DATETIME/DATE 声明列的字符串 → datetime（ISO8601 解析，非法值置 NULL）
      - 模型声明 NOT NULL 且带标量默认值、而旧行为 NULL 的格子 → 按默认回填
        （Callable 默认如 uuid4/now 不参与；回填数量逐表打印以便审计）
    """
    out = frame[[c for c in kept_names if c in frame.columns]].copy()
    backfilled = 0
    for col_name in out.columns:
        series = out[col_name]
        if series.dtype != object:
            continue
        sample = next((v for v in series if not _safe_null(v)), None)
        if sample is None:
            continue
        if isinstance(sample, (dict, list)):
            out[col_name] = series.map(
                lambda v: None if _safe_null(v)
                else (json.dumps(v, ensure_ascii=False, default=str)
                      if isinstance(v, (dict, list)) else v))
            continue
        src_col = next((c for c in src_meta.columns
                        if c.name == col_name), None)
        if src_col is None:
            continue
        if isinstance(src_col.type, sa.Boolean):
            out[col_name] = series.map(
                lambda v: None if _safe_null(v) else bool(v))
        elif isinstance(src_col.type, (sa.DateTime, sa.Date)):
            out[col_name] = pd.to_datetime(series, errors="coerce",
                                           format="ISO8601")

    # 模型新增非空列：旧库没有该列或值为 NULL 时按标量默认值回填
    for tgt_col in tgt_meta.columns:
        if tgt_col.name not in out.columns or tgt_col.nullable \
                or tgt_col.primary_key:
            continue
        fill_value = _scalar_default(tgt_col)
        n_missing = int(out[tgt_col.name].isna().sum())
        if not n_missing or fill_value is None:
            continue
        out[tgt_col.name] = out[tgt_col.name].fillna(fill_value)
        backfilled += n_missing
    return out, backfilled


def main() -> None:
    args = parse_args()
    src_path, tgt_uri = load_endpoints()

    # 延迟导入：确保已完成环境变量与 sys.path 准备
    from app.database import Base
    import app.models  # noqa: F401 — 将全部模型注册进 Base.metadata

    src_uri = ("sqlite:///" + str(src_path).replace("\\", "/"))
    src_engine = sa.create_engine(src_uri)
    tgt_engine = sa.create_engine(tgt_uri)

    # 1. 反射源库，圈定可迁移范围 -------------------------------------------
    md_src = sa.MetaData()
    md_src.reflect(bind=src_engine)

    def _is_internal(name: str) -> bool:
        return name in _INTERNAL_TABLES or \
            name.startswith(_INTERNAL_TABLES_PREFIX)

    source_table_names = {
        n for n in md_src.tables if not _is_internal(n)
    }

    model_tables = dict(Base.metadata.tables)
    transferable = {
        key: tbl for key, tbl in model_tables.items()
        if key in source_table_names
    }
    source_only = sorted(source_table_names - set(model_tables))
    model_only = sorted(set(model_tables) - set(md_src.tables))

    print(f"[1/5] 模型表 {len(model_tables)} 张 | 可迁移 {len(transferable)} 张 "
          f"| 源库孤儿表 {len(source_only)} 张 | 模型新表(空库创建) {len(model_only)} 张")
    if source_only:
        print(f"    跳过（源库有、模型无）: {source_only}")
    if model_only:
        print(f"    新建为空表（模型有、源库无）: {model_only}")

    # 2. 目标库 schema：全部来自模型元数据 -----------------------------------
    existing = set(sa.inspect(tgt_engine).get_table_names())
    if args.drop_existing:
        # 通过反射元数据删除：模型里的部分外键是匿名的（无命名约定），
        # 直接用 Base.metadata.drop_all 会因无法编译 DROP CONSTRAINT 而失败
        tgt_md = sa.MetaData()
        tgt_md.reflect(bind=tgt_engine)
        tgt_md.drop_all(bind=tgt_engine)
        print("[2/5] 已清空目标库旧表")
    else:
        absent = [key for key in model_tables if key not in existing]
        if absent:
            _fail(f"目标库缺少 {len(absent)} 张表且未启用 --drop-existing: "
                  f"{absent[:10]}")

    Base.metadata.create_all(bind=tgt_engine)
    print("[2/5] 目标库按模型 schema 建表完成")

    # 3. 逐表拷贝（拓扑序） ---------------------------------------------------
    started = time.monotonic()
    row_counts: dict[str, tuple[int, int]] = {}
    failed: list[str] = []
    with src_engine.connect() as reader_conn:
        for tgt_tbl in Base.metadata.sorted_tables:
            if tgt_tbl.name not in transferable:
                continue
            src_tbl = md_src.tables[tgt_tbl.name]
            kept_names = [c.name for c in src_tbl.columns]
            try:
                raw_frame = pd.read_sql_table(tgt_tbl.name, con=reader_conn)
                frame, n_backfill = coerce_frame(
                    raw_frame, src_tbl, kept_names, tgt_tbl)
                if n_backfill:
                    print(f"    {tgt_tbl.name}: 按模型默认值回填 "
                          f"{n_backfill} 个缺失非空字段")

                # 源库历史重复行会直接击穿 PG 唯一约束：按约束列去重保首条
                for uniq_cols in _unique_col_groups(tgt_tbl):
                    if any(c not in frame.columns for c in uniq_cols):
                        continue
                    dup_mask = frame.duplicated(subset=uniq_cols,
                                                keep="first")
                    if dup_mask.any():
                        print(f"    {tgt_tbl.name}: 唯一约束{uniq_cols} "
                              f"去重 {int(dup_mask.sum())} 行（保首条）")
                        frame = frame[~dup_mask]

                # 源库不受外键约束产生的孤儿行：父表已完成迁移时剔除并报告
                for fk in tgt_tbl.foreign_keys:
                    child_name = fk.parent.name
                    parent_name = fk.column.table.name
                    if child_name not in frame.columns \
                            or parent_name not in row_counts \
                            or parent_name == tgt_tbl.name:
                        continue
                    with tgt_engine.connect() as pc:
                        parent_values = {
                            str(r[0]) for r in pc.execute(sa.select(
                                model_tables[parent_name].c[fk.column.name]))
                        }
                    raw_keys = frame[child_name]
                    norm_keys = raw_keys.map(
                        lambda v: None if _safe_null(v) else str(v))
                    bad_mask = norm_keys.notna() & ~norm_keys.isin(parent_values)
                    if bad_mask.any():
                        print(f"    {tgt_tbl.name}: 剔除孤儿行 "
                              f"{int(bad_mask.sum())} 条（{child_name} "
                              f"在 {parent_name} 无对应记录）")
                        frame = frame[~bad_mask]

                n_src = int(len(frame))
                n_tgt = 0
                if n_src:
                    frame.to_sql(tgt_tbl.name, con=tgt_engine,
                                 if_exists="append", index=False,
                                 chunksize=args.batch_size)
                with tgt_engine.connect() as vc:
                    n_tgt = int(vc.execute(
                        sa.select(sa.func.count()).select_from(tgt_tbl)
                    ).scalar() or 0)
                row_counts[tgt_tbl.name] = (n_src, n_tgt)
                print(f"    {tgt_tbl.name}: {n_src} -> {n_tgt}")
            except Exception as e:  # noqa: BLE001 单表失败不阻断其余表
                failed.append(tgt_tbl.name)
                print(f"    {tgt_tbl.name}: FAILED ({e})")
                row_counts[tgt_tbl.name] = (
                    row_counts.get(tgt_tbl.name, (-1, -1))[0], -1)
    print(f"[3/5] 数据拷贝完成，用时 {time.monotonic() - started:.1f}s"
          f"（SERIAL 对齐请接着执行 align_pg_sequences.sql）")

    # 4. 对账 -----------------------------------------------------------------
    mismatched = {
        key: cnt for key, cnt in row_counts.items()
        if cnt[0] != cnt[1] or cnt[1] < 0
    }
    total_src = sum(c[0] for c in row_counts.values())
    total_tgt = sum(max(c[1], 0) for c in row_counts.values())
    print("[4/5] 行数对账: "
          f"{len(row_counts)} 表, 总计 {total_src} -> {total_tgt}, "
          f"不一致 {len(mismatched)}, 失败 {len(failed)}")
    if failed:
        print(f"    迁移失败表: {failed}")
    for key, cnt in sorted(mismatched.items()):
        print(f"    MISMATCH {key}: {cnt[0]} -> {cnt[1]}")

    # 孤儿行抽查（历史脏数据只报告不修复）
    orphan_issues: list[str] = []
    for name, tbl in model_tables.items():
        if name not in transferable:
            continue
        for fk in tbl.foreign_keys:
            child_col = fk.parent
            parent_col = fk.column
            probe = (
                sa.select(sa.func.count()).select_from(tbl)
                .where(child_col.isnot(None))
                .where(~sa.select(parent_col)
                       .where(child_col == parent_col).exists())
            )
            try:
                with tgt_engine.connect() as vc:
                    n_orphan = int(vc.execute(probe).scalar() or 0)
                if n_orphan:
                    orphan_issues.append(
                        f"{tbl.name}.{child_col.name} -> "
                        f"{parent_col.table.name}.{parent_col.name}: "
                        f"{n_orphan} 孤儿行")
            except sa.exc.SQLAlchemyError:
                pass
    if orphan_issues:
        print(f"    孤儿行警告 {len(orphan_issues)} 处:")
        for issue in orphan_issues[:20]:
            print(f"      {issue}")

    # 5. 迁移版本对齐 ---------------------------------------------------------
    # 必须用独立子进程：settings 在本进程启动时已按 dev 配置实例化，
    # 进程内改 DATABASE_URL 无法影响它；而 pydantic-settings 中真实环境变量
    # 优先级高于 .env 文件，新进程能正确读到目标库地址。
    if args.stamp_head:
        env_overrides = dict(os.environ)
        env_overrides["DATABASE_URL"] = tgt_uri
        done = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "alembic", "stamp", "head"],
            cwd=str(BACKEND_DIR), env=env_overrides,
            capture_output=True, text=True,
        )
        if done.returncode != 0:
            print(f"[5/5] alembic stamp head 失败:\n{done.stderr[-500:]}")
            sys.exit(3)
        print("[5/5] 目标库迁移版本已对齐 head")

    if failed or mismatched:
        print("\nRESULT: FAILED — 存在迁移失败或行数不一致的表")
        sys.exit(2)
    print("\nRESULT: OK — 全部表迁移且行数一致")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
