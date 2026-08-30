"""把 embeddings_export.jsonl 生成纯 DML 的 restore_embeddings.sql。

服务器端 psql 直接执行；id 由 gen_random_uuid() 生成（PG13+ 内置）。
幂等：无唯一键可冲突，配合 --clear 全量重建使用（导出端先 --clear 再导出）。

用法（本地）:
    py -3.13 scripts/gen_embeddings_sql.py
输出: 与脚本同目录 restore_embeddings.sql
服务器: docker cp restore_embeddings.sql <db容器>:/tmp/ && \
        docker exec <db容器> psql -U gradpath -d gradpath -f /tmp/restore_embeddings.sql
"""

import json
import os
from pathlib import Path

SRC = Path(os.environ.get("EMB_SRC", Path(__file__).resolve().parent / "embeddings_export.jsonl"))
OUT = Path(os.environ.get("EMB_OUT", Path(__file__).resolve().parent / "restore_embeddings.sql"))


def literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False)
    else:
        s = str(v)
    return "'" + s.replace("'", "''") + "'"


def main() -> None:
    n = 0
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("-- 自动生成：document_embeddings 恢复包（见 backend/scripts/gen_embeddings_sql.py）\n")
        for line in SRC.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            f.write(
                'INSERT INTO "document_embeddings" '
                '("id","source_table","source_id","chunk_index","content","doc_metadata","embedding_vector") '
                f"VALUES (gen_random_uuid(),{literal(r['source_table'])},{literal(str(r['source_id']))},"
                f"{literal(r.get('chunk_index', 0))},{literal(r.get('content'))},"
                f"{literal(r.get('doc_metadata'))},{literal(str(r['embedding']))}) "
                "ON CONFLICT DO NOTHING;\n"
            )
            n += 1
    print(f"{n} 条 INSERT → {OUT}")


if __name__ == "__main__":
    main()
