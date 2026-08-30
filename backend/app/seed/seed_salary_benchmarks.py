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


# 解析结果按数据目录缓存 — JSON 是静态的，测试套件里每个测试重读 2 万行纯属浪费
_SALARY_RECORDS_CACHE: dict[str, tuple[dict[str, Any], ...]] = {}


def _load_real_salaries_cached(data_dir: str) -> tuple[dict[str, Any], ...]:
    cached = _SALARY_RECORDS_CACHE.get(data_dir)
    if cached is None:
        cached = tuple(_load_real_salaries())
        _SALARY_RECORDS_CACHE[data_dir] = cached
    return cached


def seed_salary_benchmarks(db: Session) -> int:
    """插入薪资基准种子数据（幂等：若该公司+岗位+城市+级别+年份已存在则跳过）。

    数据全部来自真实调研 JSON，不做任何推导/放大。
    批量实现：一次取回已存在键 + add_all 单次 commit（原逐行 2 万次存在性查询，
    在测试套件里每个测试要跑一遍，单次 20+ 秒是最大时间浪费点）。

    Returns:
        新插入的记录数量
    """
    all_records = _load_real_salaries_cached(str(_real_data_dir()))
    existing = {
        (company, position, city, level, year)
        for company, position, city, level, year in db.query(
            SalaryBenchmark.company,
            SalaryBenchmark.position,
            SalaryBenchmark.city,
            SalaryBenchmark.experience_level,
            SalaryBenchmark.year,
        ).all()
    }
    new_objs: list[SalaryBenchmark] = []
    for rec in all_records:
        key = (
            rec["company"],
            rec["position"],
            rec["city"],
            rec["experience_level"],
            rec["year"],
        )
        if key in existing:
            continue
        existing.add(key)
        new_objs.append(SalaryBenchmark(**rec))
    if not new_objs:
        return 0
    db.add_all(new_objs)
    db.commit()
    return len(new_objs)
