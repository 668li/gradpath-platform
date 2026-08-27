# backend/app/seed/seed_salary_benchmarks.py
"""薪资基准种子数据 — 导入真实市场调研薪资数据。

数据来源：``app/crawlers/real_data/salary_real.json`` 与 ``salary_expand.json``
（爬虫抓取的真实市场调研数据，source=market_research，2025 年口径，单位：元/月）。

注意：原版本（SOURCE 标榜 kaggle 实为系数推导的假数据）已摘除。
本脚本只导入真实数据文件，不生成任何推导数据。
"""

import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.salary_benchmark import SalaryBenchmark

SOURCE = "market_research"
YEAR = 2025

_SALARY_FILES = ["salary_real.json", "salary_expand.json"]


def _real_data_dir() -> Path:
    """真实数据目录。可用 GRADPATH_REAL_DATA_DIR 覆盖（CI 无本地抓取数据时指向仓库内样本夹具）。"""
    override = os.environ.get("GRADPATH_REAL_DATA_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "app" / "crawlers" / "real_data"


def _load_real_salaries() -> list[dict[str, Any]]:
    """加载真实薪资 JSON，返回与 SalaryBenchmark 模型字段一致的数据列表。"""
    records: list[dict[str, Any]] = []
    for filename in _SALARY_FILES:
        path = _real_data_dir() / filename
        if not path.exists():
            raise FileNotFoundError(
                f"真实薪资数据文件不存在: {path}（请确认 real_data 数据已就位）"
            )
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"薪资数据文件格式错误（应为列表）: {path}")
        for rec in data:
            records.append(
                {
                    "company": rec["company"],
                    "position": rec["position"],
                    "city": rec.get("city"),
                    "experience_level": rec["experience_level"],
                    "salary_min": rec["salary_min"],
                    "salary_median": rec["salary_median"],
                    "salary_max": rec["salary_max"],
                    "source": rec.get("source", SOURCE),
                    "year": rec.get("year", YEAR),
                }
            )
    return records


def seed_salary_benchmarks(db: Session) -> int:
    """插入薪资基准种子数据（幂等：若该公司+岗位+城市+级别+年份已存在则跳过）。

    数据全部来自真实调研 JSON，不做任何推导/放大。

    Returns:
        新插入的记录数量
    """
    all_records = _load_real_salaries()
    inserted = 0
    for rec in all_records:
        existing = (
            db.query(SalaryBenchmark)
            .filter(
                SalaryBenchmark.company == rec["company"],
                SalaryBenchmark.position == rec["position"],
                SalaryBenchmark.city == rec["city"],
                SalaryBenchmark.experience_level == rec["experience_level"],
                SalaryBenchmark.year == rec["year"],
            )
            .first()
        )
        if existing:
            continue
        db.add(SalaryBenchmark(**rec))
        inserted += 1
    db.commit()
    return inserted
