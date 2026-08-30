"""在生产容器内恢复 user_id 外键导致的丢表数据。

背景见 export_restore_bundle.py：生产 users 是迁移后新建的（UUID 带连字符），
本地 32 位 user_id 全部对不上，引用 users 的表在迁移时被外键整表拒绝。
本脚本把这些表按 jsonl 包恢复，user_id 统一重映射到生产的系统用户。

使用方法:
    docker cp restore_bundle.jsonl <backend容器>:/tmp/
    docker exec <backend容器> python scripts/restore_user_fk_data.py /tmp/restore_bundle.jsonl

幂等：按 id 跳过已存在行，可安全重跑。
"""

import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from app.database import Base, SessionLocal
from app.models import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_USER_EMAIL = "system@gradpath.local"


def model_for(table: str):
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tablename__", None) == table:
            return cls
    return None


def coerce(column, value):
    """按模型列类型矫正 jsonl 反序列化后的值。"""
    if value is None:
        return None
    try:
        py = column.type.python_type
    except NotImplementedError:
        py = str
    if py is datetime or py is date:
        return datetime.fromisoformat(str(value))
    if py is bool:
        return bool(value)
    if py is int:
        return int(value)
    if py is float:
        return float(value)
    return value


def main() -> None:
    if len(sys.argv) < 2:
        logger.error("用法: python scripts/restore_user_fk_data.py <jsonl路径>")
        sys.exit(1)
    source = Path(sys.argv[1]).resolve()
    lines = source.read_text(encoding="utf-8").splitlines()
    logger.info("读取 %d 行", len(lines))

    db = SessionLocal()
    try:
        system_user = (
            db.query(User).filter(User.email == SYSTEM_USER_EMAIL).first()
        )
        if system_user is None:
            logger.error("找不到系统用户 %s，中止", SYSTEM_USER_EMAIL)
            sys.exit(1)
        system_uid = str(system_user.id)
        logger.info("user_id 统一重映射 → %s", system_uid)

        restored = skipped = bad = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                table = item["table"]
                rec = item["record"]
                model = model_for(table)
                if model is None:
                    logger.warning("未知表 %s，跳过", table)
                    bad += 1
                    continue
                cols = {c.name: c for c in model.__table__.columns}
                pk = cols[("id" if "id" in cols else list(cols)[0])]
                rid = rec.get(pk.name)
                exists = (
                    db.query(model).filter(pk == rid).first() is not None
                    if rid is not None
                    else False
                )
                if exists:
                    skipped += 1
                    continue
                obj = model()
                for name, col in cols.items():
                    if name not in rec:
                        continue
                    v = rec[name]
                    if name == "user_id":
                        v = system_uid
                    setattr(obj, name, coerce(col, v))
                db.add(obj)
                db.commit()
                restored += 1
            except Exception as e:  # noqa: BLE001 — 单行失败不中断整体恢复
                db.rollback()
                bad += 1
                logger.warning("恢复失败: %s — %s", str(e)[:120], line[:80])
        logger.info("恢复完成: 新增 %d, 跳过已存在 %d, 失败 %d", restored, skipped, bad)
    finally:
        db.close()


if __name__ == "__main__":
    main()
