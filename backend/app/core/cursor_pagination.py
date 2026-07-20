"""游标分页工具 — 替代 offset 分页，避免深页性能退化。

用最后一条记录的 id 作为游标，前端传回游标即可精确取下一页，
无需 COUNT(*) 或 OFFSET。适用于按 created_at/id 排序的列表。
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query


def encode_cursor(created_at: Any, item_id: str) -> str:
    """将 (created_at, id) 编码为不透明游标字符串。"""
    payload = {"ts": str(created_at), "id": item_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> dict | None:
    """解码游标字符串，失败返回 None。"""
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except Exception:
        return None


def _parse_cursor_ts(cursor_ts: Any) -> Any:
    """将游标中的 ts 字段解析为 datetime 对象。

    SQLAlchemy 在 SQLite 下将 DateTime 列以 TEXT 形式存储（默认
    ``'YYYY-MM-DD HH:MM:SS.ffffff'``，带空格分隔符与微秒）。如果直接把
    字符串游标传给 ``time_col < cursor_ts``，SQLite 会按字符串逐字符比较，
    而前端/服务端生成的 ts 字符串通常使用 ISO 8601（``T`` 分隔符，无微秒），
    导致 ``'2026-07-20 10:00:00.000000' < '2026-07-20T10:00:00'`` 被判定
    为 True（空格 0x20 < 'T' 0x54），从而错误地把游标记录本身也包含进结果。

    将 ts 解析为 ``datetime`` 对象后，SQLAlchemy 会以与存储一致的格式
    绑定参数，比较按 datetime 语义进行，结果正确。

    支持：
    - tz-aware / tz-naive ISO 字符串（含/不含微秒）
    - 已是 datetime 对象（直接返回）
    - 解析失败返回原值，交由数据库驱动处理（向后兼容）
    """
    if isinstance(cursor_ts, datetime):
        return cursor_ts
    if isinstance(cursor_ts, str):
        try:
            return datetime.fromisoformat(cursor_ts)
        except ValueError:
            return cursor_ts
    return cursor_ts


def apply_cursor_filter(
    query: Query,
    cursor: str | None,
    *,
    time_col,
    id_col,
    descending: bool = True,
) -> Query:
    """对 query 应用游标过滤条件。

    Args:
        query: 已有筛选条件的 SQLAlchemy Query
        cursor: 游标字符串，None 表示第一页
        time_col: 排序时间列（如 Model.created_at）
        id_col: 主键列（如 Model.id）
        descending: True 为倒序（默认），False 为正序

    Returns:
        追加了游标条件的 Query
    """
    if not cursor:
        return query

    data = decode_cursor(cursor)
    if not data or "ts" not in data or "id" not in data:
        return query

    # 解析为 datetime 对象，确保 SQLAlchemy 以 DateTime 参数绑定
    # 避免 SQLite TEXT 列与字符串游标因格式差异导致的错误字符串比较
    cursor_ts = _parse_cursor_ts(data["ts"])
    cursor_id = data["id"]

    if descending:
        # created_at < cursor_ts OR (created_at == cursor_ts AND id < cursor_id)
        return query.filter(
            or_(
                time_col < cursor_ts,
                and_(time_col == cursor_ts, id_col < cursor_id),
            )
        )
    else:
        return query.filter(
            or_(
                time_col > cursor_ts,
                and_(time_col == cursor_ts, id_col > cursor_id),
            )
        )
