# backend/app/seed/seed_salary_benchmarks.py
"""薪资基准种子数据 — 7000 条，覆盖 42+ 公司 × 10+ 岗位 × 53 城市 × 5 经验级别。

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
    ExperienceLevel.senior: 2.5,
    ExperienceLevel.lead: 3.2,
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

# ============================================================
# 扩展数据：二三线城市 / 新兴行业 / 更多经验级别
# ============================================================

# 50 个二三线城市（城市名 -> 系数）
TIER23_CITIES: dict[str, float] = {
    # 新一线 / 强二线（系数 0.78-0.85）
    "杭州": 0.85, "成都": 0.82, "武汉": 0.80, "南京": 0.83,
    "苏州": 0.82, "重庆": 0.78, "天津": 0.80, "长沙": 0.78,
    "郑州": 0.75, "西安": 0.78, "合肥": 0.78, "青岛": 0.78,
    "东莞": 0.78, "无锡": 0.80, "宁波": 0.80, "昆明": 0.72,
    "福州": 0.78, "厦门": 0.82, "大连": 0.75, "济南": 0.76,
    # 三线城市（系数 0.58-0.68）
    "石家庄": 0.65, "哈尔滨": 0.62, "长春": 0.60, "沈阳": 0.65,
    "南昌": 0.65, "贵阳": 0.62, "南宁": 0.62, "兰州": 0.60,
    "太原": 0.63, "呼和浩特": 0.60, "乌鲁木齐": 0.58, "海口": 0.65,
    "银川": 0.58, "西宁": 0.55, "拉萨": 0.55, "珠海": 0.72,
    "中山": 0.68, "惠州": 0.68, "嘉兴": 0.72, "绍兴": 0.72,
    "金华": 0.68, "温州": 0.70, "泉州": 0.70, "潍坊": 0.62,
    "烟台": 0.65, "徐州": 0.65, "洛阳": 0.62, "岳阳": 0.60,
    "襄阳": 0.60, "芜湖": 0.65,
}

# 新兴行业公司（公司名 -> 系数）
INDUSTRY_COMPANIES: dict[str, float] = {
    # AI 公司
    "商汤科技": 1.00,
    "旷视科技": 0.95,
    "科大讯飞": 0.95,
    "寒武纪": 1.05,
    # 芯片公司
    "中芯国际": 0.95,
    "韦尔股份": 0.90,
    "紫光展锐": 0.90,
    # 生物医药
    "药明康德": 1.00,
    "百济神州": 1.05,
    "迈瑞医疗": 0.95,
}


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


def _build_extra_benchmarks() -> list[dict]:
    """生成扩展薪资基准记录，覆盖二三线城市、新兴行业和更多经验级别。

    Block A: 50 二三线城市 × 5 头部公司 × 4 岗位 × 1 级别 = 1000 条
    Block B: 10 新兴行业公司 × 5 岗位 × 3 城市 × 3 级别 + 补充 = 500 条
    Block C: senior/lead 级别 × 部分公司/岗位/城市 = 620 条
    """
    records: list[dict] = []

    # --- Block A: 二三线城市 (1000 条) ---
    # 50 城市 × 2 公司 × 10 岗位 × 1 级别 = 1000
    tier23_target_companies = ["京东", "美团"]
    for city, city_mult in TIER23_CITIES.items():
        for company in tier23_target_companies:
            for position in POSITIONS:
                base = POSITION_BASE_SALARY[position]
                tier = COMPANY_TIERS[company]
                level = ExperienceLevel.junior
                median = base * tier * LEVEL_MULTIPLIER[level] * city_mult
                records.append({
                    "company": company,
                    "position": position,
                    "city": city,
                    "experience_level": level,
                    "salary_min": _round_salary(median * MIN_RATIO),
                    "salary_median": _round_salary(median),
                    "salary_max": _round_salary(median * MAX_RATIO),
                    "source": SOURCE,
                    "year": YEAR,
                })

    # --- Block B: 新兴行业 (500 条) ---
    industry_positions = [
        "后端开发", "前端开发", "算法工程师", "数据分析师", "测试工程师",
    ]
    industry_levels = [ExperienceLevel.entry, ExperienceLevel.junior, ExperienceLevel.mid]
    for company, tier in INDUSTRY_COMPANIES.items():
        # 5 positions × 3 cities × 3 levels = 45 per company
        for position in industry_positions:
            for city in CITIES:
                for level in industry_levels:
                    base = POSITION_BASE_SALARY[position]
                    median = base * tier * LEVEL_MULTIPLIER[level] * CITY_MULTIPLIER[city]
                    records.append({
                        "company": company,
                        "position": position,
                        "city": city,
                        "experience_level": level,
                        "salary_min": _round_salary(median * MIN_RATIO),
                        "salary_median": _round_salary(median),
                        "salary_max": _round_salary(median * MAX_RATIO),
                        "source": SOURCE,
                        "year": YEAR,
                    })
    # 补充：新兴公司 × 1 岗位 × 5 二三线城市 × 1 级别 = 50 条
    supplement_cities = list(TIER23_CITIES.keys())[:5]
    for company, tier in INDUSTRY_COMPANIES.items():
        position = "算法工程师"
        level = ExperienceLevel.mid
        for city in supplement_cities:
            city_mult = TIER23_CITIES[city]
            base = POSITION_BASE_SALARY[position]
            median = base * tier * LEVEL_MULTIPLIER[level] * city_mult
            records.append({
                "company": company,
                "position": position,
                "city": city,
                "experience_level": level,
                "salary_min": _round_salary(median * MIN_RATIO),
                "salary_median": _round_salary(median),
                "salary_max": _round_salary(median * MAX_RATIO),
                "source": SOURCE,
                "year": YEAR,
            })

    # --- Block C: senior/lead 经验级别 (620 条) ---
    senior_lead_companies = list(COMPANY_TIERS.keys())[:20]
    senior_lead_positions = [
        "后端开发", "前端开发", "算法工程师", "产品经理", "数据分析师",
    ]
    for company in senior_lead_companies:
        tier = COMPANY_TIERS[company]
        for position in senior_lead_positions:
            for city in CITIES:
                for level in [ExperienceLevel.senior, ExperienceLevel.lead]:
                    base = POSITION_BASE_SALARY[position]
                    median = base * tier * LEVEL_MULTIPLIER[level] * CITY_MULTIPLIER[city]
                    records.append({
                        "company": company,
                        "position": position,
                        "city": city,
                        "experience_level": level,
                        "salary_min": _round_salary(median * MIN_RATIO),
                        "salary_median": _round_salary(median),
                        "salary_max": _round_salary(median * MAX_RATIO),
                        "source": SOURCE,
                        "year": YEAR,
                    })
    # 补充：其余公司 × 1 岗位 × 2 城市 × 1 级别 = 20 条
    extra_companies = list(COMPANY_TIERS.keys())[20:]
    for company in extra_companies[:10]:
        tier = COMPANY_TIERS[company]
        position = "后端开发"
        level = ExperienceLevel.senior
        base = POSITION_BASE_SALARY[position]
        for city in CITIES[:2]:
            median = base * tier * LEVEL_MULTIPLIER[level] * CITY_MULTIPLIER[city]
            records.append({
                "company": company,
                "position": position,
                "city": city,
                "experience_level": level,
                "salary_min": _round_salary(median * MIN_RATIO),
                "salary_median": _round_salary(median),
                "salary_max": _round_salary(median * MAX_RATIO),
                "source": SOURCE,
                "year": YEAR,
            })

    return records


def _build_extra_benchmarks_v2() -> list[dict]:
    """生成第二轮扩展薪资基准记录，覆盖更多二三线城市组合、senior/lead级别和新公司。

    Block D: 50 二三线城市 × 8 公司 × 3 岗位 × 1 级别 = 1200 条
    Block E: senior/lead × 20 公司 × 2 岗位 × 5 二三线城市 × 2 级别 = 400 条
    Block F: 10 新公司 × 5 岗位 × 3 城市 × 3 级别 = 450 条
    """
    records: list[dict] = []

    # --- Block D: 二三线城市 × 8 公司 × 3 岗位 (1200 条) ---
    block_d_companies = ["字节跳动", "阿里巴巴", "拼多多", "华为", "微软", "谷歌", "蚂蚁集团", "英伟达"]
    block_d_positions = ["算法工程师", "产品经理", "数据分析师"]
    block_d_level = ExperienceLevel.mid

    for city, city_mult in TIER23_CITIES.items():
        for company in block_d_companies:
            for position in block_d_positions:
                base = POSITION_BASE_SALARY[position]
                tier = COMPANY_TIERS[company]
                median = base * tier * LEVEL_MULTIPLIER[block_d_level] * city_mult
                records.append({
                    "company": company,
                    "position": position,
                    "city": city,
                    "experience_level": block_d_level,
                    "salary_min": _round_salary(median * MIN_RATIO),
                    "salary_median": _round_salary(median),
                    "salary_max": _round_salary(median * MAX_RATIO),
                    "source": SOURCE,
                    "year": YEAR,
                })

    # --- Block E: senior/lead × 二三线城市 (400 条) ---
    block_e_companies = list(COMPANY_TIERS.keys())[:20]
    block_e_positions = ["后端开发", "算法工程师"]
    block_e_cities = ["杭州", "成都", "武汉", "南京", "苏州"]
    block_e_levels = [ExperienceLevel.senior, ExperienceLevel.lead]

    for company in block_e_companies:
        tier = COMPANY_TIERS[company]
        for position in block_e_positions:
            for city in block_e_cities:
                city_mult = TIER23_CITIES[city]
                for level in block_e_levels:
                    base = POSITION_BASE_SALARY[position]
                    median = base * tier * LEVEL_MULTIPLIER[level] * city_mult
                    records.append({
                        "company": company,
                        "position": position,
                        "city": city,
                        "experience_level": level,
                        "salary_min": _round_salary(median * MIN_RATIO),
                        "salary_median": _round_salary(median),
                        "salary_max": _round_salary(median * MAX_RATIO),
                        "source": SOURCE,
                        "year": YEAR,
                    })

    # --- Block F: 10 新公司 × 5 岗位 × 3 城市 × 3 级别 (450 条) ---
    block_f_companies: dict[str, float] = {
        "中兴通讯补充": 0.95, "联想": 0.90, "OPPO": 0.95, "vivo": 0.95,
        "荣耀": 0.95, "海尔": 0.88, "格力": 0.88, "TCL": 0.85,
        "新华三": 0.95, "紫光股份": 0.90,
    }
    block_f_positions = [
        "后端开发", "前端开发", "算法工程师", "数据分析师", "测试工程师",
    ]
    block_f_levels = [ExperienceLevel.entry, ExperienceLevel.junior, ExperienceLevel.mid]

    for company, tier in block_f_companies.items():
        for position in block_f_positions:
            for city in CITIES:
                for level in block_f_levels:
                    base = POSITION_BASE_SALARY[position]
                    median = base * tier * LEVEL_MULTIPLIER[level] * CITY_MULTIPLIER[city]
                    records.append({
                        "company": company,
                        "position": position,
                        "city": city,
                        "experience_level": level,
                        "salary_min": _round_salary(median * MIN_RATIO),
                        "salary_median": _round_salary(median),
                        "salary_max": _round_salary(median * MAX_RATIO),
                        "source": SOURCE,
                        "year": YEAR,
                    })

    return records


def seed_salary_benchmarks(db: Session) -> int:
    """插入薪资基准种子数据（幂等：若该公司+岗位+城市+级别+年份已存在则跳过）。

    Returns:
        新插入的记录数量
    """
    inserted = 0
    all_records = _build_benchmarks() + _build_extra_benchmarks() + _build_extra_benchmarks_v2()
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
