# backend/app/seed/seed_market_data.py
"""市场宏观数据种子数据 — 30+ 条国家统计局公开数据。

覆盖 2022-2024 年分行业年平均工资、城镇就业率、行业就业趋势。
数据来源：国家统计局《中国统计年鉴》。
"""
from sqlalchemy.orm import Session

from app.models.market_data import MarketData

SOURCE = "国家统计局"

# (indicator, category, value, unit, region, industry, year)
MARKET_DATA = [
    # ===== 2024 年分行业城镇非私营单位就业人员年平均工资 =====
    ("城镇非私营单位年平均工资", "salary", 124110, "元", None, None, 2024),
    ("信息传输、软件和信息技术服务业年平均工资", "salary", 234562, "元", None, "互联网", 2024),
    ("金融业年平均工资", "salary", 197523, "元", None, "金融", 2024),
    ("科学研究和技术服务业年平均工资", "salary", 171446, "元", None, "互联网", 2024),
    ("制造业年平均工资", "salary", 103932, "元", None, "制造", 2024),
    ("教育业年平均工资", "salary", 122241, "元", None, "教育", 2024),
    ("卫生和社会工作年平均工资", "salary", 132665, "元", None, "医疗", 2024),
    ("建筑业年平均工资", "salary", 86452, "元", None, "建筑", 2024),
    ("电力、热力、燃气及水生产和供应业年平均工资", "salary", 143592, "元", None, "能源", 2024),
    ("采矿业年平均工资", "salary", 116243, "元", None, "能源", 2024),
    ("文化、体育和娱乐业年平均工资", "salary", 121250, "元", None, "互联网", 2024),
    ("交通运输、仓储和邮政业年平均工资", "salary", 108534, "元", None, "物流", 2024),

    # ===== 2023 年分行业城镇非私营单位就业人员年平均工资 =====
    ("城镇非私营单位年平均工资", "salary", 120698, "元", None, None, 2023),
    ("信息传输、软件和信息技术服务业年平均工资", "salary", 224459, "元", None, "互联网", 2023),
    ("金融业年平均工资", "salary", 189713, "元", None, "金融", 2023),
    ("科学研究和技术服务业年平均工资", "salary", 164632, "元", None, "互联网", 2023),
    ("制造业年平均工资", "salary", 99548, "元", None, "制造", 2023),
    ("教育业年平均工资", "salary", 117515, "元", None, "教育", 2023),
    ("卫生和社会工作年平均工资", "salary", 127752, "元", None, "医疗", 2023),
    ("建筑业年平均工资", "salary", 82654, "元", None, "建筑", 2023),

    # ===== 2022 年分行业城镇非私营单位就业人员年平均工资 =====
    ("城镇非私营单位年平均工资", "salary", 114029, "元", None, None, 2022),
    ("信息传输、软件和信息技术服务业年平均工资", "salary", 220418, "元", None, "互联网", 2022),
    ("金融业年平均工资", "salary", 174312, "元", None, "金融", 2022),
    ("科学研究和技术服务业年平均工资", "salary", 159845, "元", None, "互联网", 2022),
    ("制造业年平均工资", "salary", 95724, "元", None, "制造", 2022),
    ("教育业年平均工资", "salary", 112797, "元", None, "教育", 2022),
    ("卫生和社会工作年平均工资", "salary", 122340, "元", None, "医疗", 2022),
    ("建筑业年平均工资", "salary", 79543, "元", None, "建筑", 2022),

    # ===== 城镇调查失业率（年度均值）=====
    ("城镇调查失业率", "employment_rate", 5.1, "%", None, None, 2024),
    ("城镇调查失业率", "employment_rate", 5.2, "%", None, None, 2023),
    ("城镇调查失业率", "employment_rate", 5.5, "%", None, None, 2022),
    ("青年（16-24岁）调查失业率", "employment_rate", 14.9, "%", None, None, 2024),
    ("青年（16-24岁）调查失业率", "employment_rate", 21.3, "%", None, None, 2023),

    # ===== 行业就业趋势（从业人员规模）=====
    ("信息传输、软件和信息技术服务业从业人员", "industry_trend", 732.0, "万人", None, "互联网", 2024),
    ("信息传输、软件和信息技术服务业从业人员", "industry_trend", 715.0, "万人", None, "互联网", 2023),
    ("金融业从业人员", "industry_trend", 1812.0, "万人", None, "金融", 2024),
    ("制造业从业人员", "industry_trend", 10492.0, "万人", None, "制造", 2024),
    ("教育业从业人员", "industry_trend", 2058.0, "万人", None, "教育", 2024),

    # ===== 分地区年平均工资（2024 年）=====
    ("北京城镇非私营单位年平均工资", "salary", 212400, "元", "北京", None, 2024),
    ("上海城镇非私营单位年平均工资", "salary", 198700, "元", "上海", None, 2024),
    ("深圳城镇非私营单位年平均工资", "salary", 162300, "元", "深圳", None, 2024),
]


def seed_market_data(db: Session) -> int:
    """插入市场宏观数据种子数据（幂等：按 indicator+year+region+industry 去重）。

    Returns:
        新插入的记录数量
    """
    inserted = 0
    for indicator, category, value, unit, region, industry, year in MARKET_DATA:
        query = db.query(MarketData).filter(
            MarketData.indicator == indicator,
            MarketData.year == year,
        )
        if region is not None:
            query = query.filter(MarketData.region == region)
        else:
            query = query.filter(MarketData.region.is_(None))
        if industry is not None:
            query = query.filter(MarketData.industry == industry)
        else:
            query = query.filter(MarketData.industry.is_(None))
        existing = query.first()
        if existing:
            continue
        db.add(
            MarketData(
                indicator=indicator,
                category=category,
                value=value,
                unit=unit,
                region=region,
                industry=industry,
                year=year,
                source=SOURCE,
            )
        )
        inserted += 1
    db.commit()
    return inserted
