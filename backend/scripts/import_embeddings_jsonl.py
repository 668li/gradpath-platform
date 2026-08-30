"""把本地导出的 embeddings jsonl 导入服务器 document_embeddings 表。

背景：生产服务器 2核4G 加载不动 Embedding 模型，向量统一在本地计算，
导出 embeddings_export.jsonl 后在本容器内导入（无需 torch/sentence-transformers）。

使用方法:
    docker cp embeddings_export.jsonl <backend容器>:/tmp/
    docker exec <backend容器> python scripts/import_embeddings_jsonl.py /tmp/embeddings_export.jsonl

幂等策略:
    默认跳过 (source_table, source_id, chunk_index) 已存在的行；
    换 Embedding 模型全量重建时先传 --clear 清空旧向量。
    注意: 向量必须由 app.config.EMBEDDING_MODEL 同一模型生成，否则查询相似度无意义。
"""

import ast
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import text

from app.database import SessionLocal
from app.models.embedding_model import DocumentEmbedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) < 2:
        logger.error("用法: python scripts/import_embeddings_jsonl.py <jsonl路径> [--clear]")
        sys.exit(1)
    source = Path(sys.argv[1]).resolve()
    if not source.is_file():
        logger.error("文件不存在: %s", source)
        sys.exit(1)
    clear = "--clear" in sys.argv

    lines = source.read_text(encoding="utf-8").splitlines()
    logger.info("读取 %d 行", len(lines))

    db = SessionLocal()
    try:
        if clear:
            logger.info("清空现有向量数据...")
            db.query(DocumentEmbedding).delete()
            db.commit()

        existing: set[tuple[str, str, int]] = {
            (r[0], str(r[1]), r[2])
            for r in db.execute(
                text("SELECT source_table, source_id, chunk_index FROM document_embeddings")
            ).fetchall()
        }

        batch: list[DocumentEmbedding] = []
        inserted = skipped = bad = 0

        def _flush() -> None:
            nonlocal inserted
            if batch:
                db.add_all(batch)
                db.commit()
                inserted += len(batch)
                batch.clear()

        for line in lines:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                vec = rec["embedding"]
                if not isinstance(vec, list) or not vec:
                    raise ValueError("空向量")
                float(vec[0])
            except Exception:  # noqa: BLE001 — 单行坏数据跳过，不中断导入
                bad += 1
                continue
            key = (rec["source_table"], str(rec["source_id"]), int(rec.get("chunk_index", 0)))
            if key in existing:
                skipped += 1
                continue
            existing.add(key)
            batch.append(
                DocumentEmbedding(
                    source_table=key[0],
                    source_id=key[1],
                    chunk_index=key[2],
                    content=rec.get("content") or "",
                    doc_metadata=rec.get("doc_metadata") or {},
                    embedding_vector=str(vec),
                )
            )
            if len(batch) >= 500:
                _flush()
                logger.info("已插入 %d 行...", inserted)
        _flush()
        logger.info("导入完成: 插入 %d, 跳过已存在 %d, 坏行 %d", inserted, skipped, bad)

        # 抽样校验：向量字符串可被 ast 反序列化
        sample = db.execute(
            text("SELECT embedding_vector FROM document_embeddings LIMIT 3")
        ).fetchall()
        for r in sample:
            ast.literal_eval(r[0])
        logger.info("抽样校验通过")
    finally:
        db.close()


if __name__ == "__main__":
    main()
