# -*- coding: utf-8 -*-
"""技能树→条件账本 转型可行性核查：gwy_position 条件字段质量审计。

只读。SQL 只有一条字面量 SELECT（拉齐所需列），全部统计在 Python 内完成，
避免任何动态 SQL 构造。输出：
1. 全表各条件字段非空率
2. 可枚举字段取值分布（可枚举性=可解析性）
3. major_req 的"不限"占比与自由文本占比
4. remarks 中证书类要求（四六级/计算机/资格证）的可挖掘率
5. 随机抽样 50 个职位的逐字段清单演示
"""
import random
import re
import sqlite3
from collections import Counter

DB = r"D:\职业规划\职业规划\gradpath.db"

CERT_PAT = re.compile(r"四六级|英语四级|英语六级|CET|计算机等级|计算机二级|资格证|证书|执业资格|普通话")

FIELDS = [
    "major_req",
    "education_req",
    "degree_req",
    "political_status",
    "min_work_years",
    "grassroots_exp_req",
    "professional_test",
    "interview_ratio",
]
FIELD_LABELS = {
    "major_req": "专业要求",
    "education_req": "学历要求",
    "degree_req": "学位要求",
    "political_status": "政治面貌",
    "min_work_years": "基层工作最低年限",
    "grassroots_exp_req": "基层工作经历要求",
    "professional_test": "专业科目考试",
    "interview_ratio": "面试比例",
}

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = conn.execute(
    "SELECT position_name, dept_name, major_req, education_req, degree_req, political_status, "
    "min_work_years, grassroots_exp_req, professional_test, interview_ratio, remarks "
    "FROM gwy_position"
)
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
total = len(rows)
records = [dict(zip(cols, r)) for r in rows]
conn.close()


def filled(v) -> bool:
    return v is not None and str(v).strip() != ""


print(f"=== 1. 全表 {total} 行，条件字段非空率 ===")
for col in FIELDS:
    n = sum(1 for r in records if filled(r[col]))
    print(f"  {FIELD_LABELS[col]:12s} {col:20s} {n:6d}  {n/total*100:5.1f}%")

print("\n=== 2. 可枚举字段取值分布 ===")
for col in FIELDS:
    if col == "major_req":
        continue  # 自由文本，单独分析
    dist = Counter(str(r[col]).strip() for r in records if filled(r[col]))
    print(f"  [{col}] 去重后 {len(dist)} 种取值，Top:")
    for v, c in dist.most_common(6):
        print(f"      {v!r:>40}  x{c}")

print("\n=== 3. major_req 质量分析 ===")
has_major = [r for r in records if filled(r["major_req"])]
unrestricted = [r for r in has_major if "不限" in str(r["major_req"])]
avg_len = sum(len(str(r["major_req"])) for r in has_major) / max(len(has_major), 1)
print(f"  有专业要求: {len(has_major)} ({len(has_major)/total*100:.1f}%)，其中含『不限』: {len(unrestricted)} ({len(unrestricted)/total*100:.1f}%)，平均长度 {avg_len:.0f} 字符")

print("\n=== 4. 证书类要求可挖掘率（remarks）===")
cert_rows = [r for r in records if CERT_PAT.search(r["remarks"] or "")]
print(f"  remarks 命中证书关键词: {len(cert_rows)} 行 ({len(cert_rows)/total*100:.1f}%)")

print("\n=== 5. 随机抽样 50 个职位：条件清单生成演示 ===")
random.seed(42)
sample = random.sample(records, 50)
coverage = [sum(1 for c in FIELDS if filled(r[c])) for r in sample]
avg_filled = sum(coverage) / len(coverage)
ge6 = sum(1 for c in coverage if c >= 6)
print(f"  抽样 50 个职位：平均每职位可自动生成 {avg_filled:.1f} 条结构化条件；≥6 条的职位占 {ge6/50*100:.0f}%")
demo = sample[0]
print("\n  示例职位条件清单（1/50）:")
print(f"  职位: {demo['position_name']} | {demo['dept_name']}")
for c in FIELDS:
    if filled(demo[c]):
        print(f"    - {FIELD_LABELS[c]}: {demo[c]}")
if CERT_PAT.search(demo["remarks"] or ""):
    m = CERT_PAT.search(demo["remarks"])
    print(f"    - 证书要求(从备注挖掘): ...{demo['remarks'][max(0, m.start()-10):m.end()+20]}...")

print("\n=== 核查完成 ===")
