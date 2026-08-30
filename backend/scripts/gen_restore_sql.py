"""把 restore_bundle.jsonl 生成纯 DML 的 restore_data.sql（生产 psql 直接执行）。

背景见 export_restore_bundle.py。user_id 全部重映射为生产系统用户
（00000000-0000-0000-0000-000000000000，email system@gradpath.local）。
幂等：INSERT ... ON CONFLICT (id) DO NOTHING。

用法（本地）:
    py -3.13 scripts/gen_restore_sql.py
输出: 与脚本同目录 restore_data.sql
服务器: docker cp restore_data.sql <db容器>:/tmp/ && \
        docker exec <db容器> psql -U gradpath -d gradpath -f /tmp/restore_data.sql
"""

import json
from pathlib import Path

SRC = Path(__file__).resolve().parent / "restore_bundle.jsonl"
OUT = Path(__file__).resolve().parent / "restore_data.sql"

SYSTEM_UID = "00000000-0000-0000-0000-000000000000"


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
    out: list[str] = ["-- 自动生成：user_id 外键丢表数据恢复包（见 backend/scripts/gen_restore_sql.py）",
                      "BEGIN;"]
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        table = item["table"]
        rec = item["record"]
        if "user_id" in rec:
            rec["user_id"] = SYSTEM_UID
        cols = list(rec.keys())
        vals = ", ".join(literal(rec[c]) for c in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        out.append(
            f'INSERT INTO "{table}" ({col_list}) VALUES ({vals}) ON CONFLICT (id) DO NOTHING;'
        )
        n += 1
    out.append("COMMIT;")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{n} 条 INSERT → {OUT}")


if __name__ == "__main__":
    main()
