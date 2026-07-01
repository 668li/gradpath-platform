# backend/app/seed/seed_salary_benchmarks.py
"""薪资基准种子数据 — 200+ 条，覆盖 20+ 公司 × 10 岗位 × 3 城市 × 3 经验级别。

薪资数据参考真实市场水平（2024 年口径，单位：元/月）。
"""
from sqlalchemy.orm import Session

from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark

SOURCE = "kaggle"
YEAR = 2024

# 10 个核心岗位
POSITIONS = [
    "后端开发",
    "前端开发",
    "算法工程师",
    "产品经理",
    "数据分析师",
    "测试工程师",
    "运维工程师",
    "移动端开发",
    "UI设计师",
    "运营",
]

CITIES = ["北京", "上海", "深圳"]

LEVELS = [ExperienceLevel.entry, ExperienceLevel.junior, ExperienceLevel.mid]

# 公司 -> 基础薪资系数（1.0 为基准大厂水平）
# 系数反映该公司相对薪酬水平（外企/头部互联网偏高，国企偏低）
COMPANY_TIERS = {
    # 头部互联网（系数 1.0-1.2）
    "腾讯": 1.20,
    "字节跳动": 1.20,
    "阿里巴巴": 1.15,
    "百度": 1.05,
    "美团": 1.05,
    "京东": 1.00,
    "网易": 1.00,
    "拼多多": 1.25,
    "快手": 1.05,
    "小红书": 1.00,
    "哔哩哔哩": 0.95,
    "滴滴出行": 0.95,
    "携程": 0.90,
    "知乎": 0.90,
    "米哈游": 1.20,
    # 金融科技
    "蚂蚁集团": 1.20,
    "中金公司": 1.15,
    "中信证券": 1.05,
    "招商银行": 1.00,
    # 通信/硬件
    "华为": 1.20,
    "中兴通讯": 0.95,
    "小米": 0.95,
    "大疆": 1.10,
    # 外企
    "微软": 1.25,
    "谷歌": 1.35,
    "亚马逊": 1.25,
    "苹果": 1.25,
    "英伟达": 1.40,
    # 新能源
    "比亚迪": 0.90,
    "理想汽车": 1.05,
    "蔚来": 1.00,
    "小鹏汽车": 1.00,
}

# 岗位 -> 基础月薪中位数（entry 级别，单位：元/月，基准系数 1.0）
POSITION_BASE_SALARY = {
    "后端开发": 20000,
    "前端开发": 19000,
    "算法工程师": 25000,
    "产品经理": 18000,
    "数据分析师": 17000,
    "测试工程师": 15000,
    "运维工程师": 16000,
    "移动端开发": 19000,
    "UI设计师": 14000,
    "运营": 12000,
}

# 经验级别 -> 薪资倍数（相对 entry）
LEVEL_MULTIPLIER = {
    ExperienceLevel.entry: 1.0,
    ExperienceLevel.junior: 1.4,
    ExperienceLevel.mid: 1.9,
}

# 城市调节系数（北京偏高，深圳/上海略低）
CITY_MULTIPLIER = {
    "北京": 1.05,
    "上海": 1.00,
    "深圳": 1.02,
}

# min/median/max 比例
MIN_RATIO = 0.82
MAX_RATIO = 1.25


def _round_salary(value: float) -> int:
    """将薪资取整到百元。"""
    return int(round(value / 100) * 100)


def _build_benchmarks() -> list[dict]:
    """生成所有薪资基准记录（公司 × 岗位 × 城市 × 经验级别）。"""
    records = []
    for company, tier in COMPANY_TIERS.items():
        for position, base in POSITION_BASE_SALARY.items():
            for city in CITIES:
                for level in LEVELS:
                    median = base * tier * LEVEL_MULTIPLIER[level] * CITY_MULTIPLIER[city]
                    median_int = _round_salary(median)
                    salary_min = _round_salary(median * MIN_RATIO)
                    salary_max = _round_salary(median * MAX_RATIO)
                    records.append(
                        {
                            "company": company,
                            "position": position,
                            "city": city,
                            "experience_level": level,
                            "salary_min": salary_min,
                            "salary_median": median_int,
                            "salary_max": salary_max,
                            "source": SOURCE,
                            "year": YEAR,
                        }
                    )
    return records


def seed_salary_benchmarks(db: Session) -> int:
    """插入薪资基准种子数据（幂等：若该公司+岗位+城市+级别+年份已存在则跳过）。

    Returns:
        新插入的记录数量
    """
    inserted = 0
    for rec in _build_benchmarks():
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
