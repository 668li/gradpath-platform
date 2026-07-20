"""教育部 / 国家统计局统计数据导入器 — 公开宏观数据预置导入。

数据来源为教育部年度教育统计公报、国家统计局《中国统计年鉴》等公开资料，
覆盖 6 个统计维度（高校毕业生/研究生报考/研究生录取/公务员报考/城镇就业/行业工资），
每维度 10 条，共 60 条。数值尽量贴近真实趋势（如毕业生人数逐年增长）。

未来可扩展为从教育部 / 统计局官网 API 真实抓取，替换 fetch() 中的预置数据。
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.market_data import MarketData


SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

_MOE_URL = "http://www.moe.gov.cn/"           # 教育部
_STATS_URL = "http://www.stats.gov.cn/"       # 国家统计局

# 预置统计数据：(indicator, category, value, unit, region, industry, year, source, source_url)
# indicator 对应任务字段 indicator_name，category 对应 indicator_category
_STATS_DATA: list[tuple] = [
    # === 1. 高校毕业生人数（按年份，2015-2024）— 教育部，10 条 ===
    ("高校毕业生人数", "graduates", 749.0, "万人", "全国", None, 2015, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 765.0, "万人", "全国", None, 2016, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 795.0, "万人", "全国", None, 2017, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 820.0, "万人", "全国", None, 2018, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 834.0, "万人", "全国", None, 2019, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 874.0, "万人", "全国", None, 2020, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 909.0, "万人", "全国", None, 2021, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 1076.0, "万人", "全国", None, 2022, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 1158.0, "万人", "全国", None, 2023, "教育部", _MOE_URL),
    ("高校毕业生人数", "graduates", 1179.0, "万人", "全国", None, 2024, "教育部", _MOE_URL),

    # === 2. 研究生报考人数（按年份）— 教育部，10 条 ===
    ("研究生报考人数", "postgrad_exam", 165.0, "万人", "全国", None, 2015, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 177.0, "万人", "全国", None, 2016, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 201.0, "万人", "全国", None, 2017, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 238.0, "万人", "全国", None, 2018, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 290.0, "万人", "全国", None, 2019, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 341.0, "万人", "全国", None, 2020, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 377.0, "万人", "全国", None, 2021, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 457.0, "万人", "全国", None, 2022, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 474.0, "万人", "全国", None, 2023, "教育部", _MOE_URL),
    ("研究生报考人数", "postgrad_exam", 438.0, "万人", "全国", None, 2024, "教育部", _MOE_URL),

    # === 3. 研究生录取人数（按年份）— 教育部，10 条 ===
    ("研究生录取人数", "postgrad_admit", 64.5, "万人", "全国", None, 2015, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 66.7, "万人", "全国", None, 2016, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 72.2, "万人", "全国", None, 2017, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 76.3, "万人", "全国", None, 2018, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 81.1, "万人", "全国", None, 2019, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 99.0, "万人", "全国", None, 2020, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 105.1, "万人", "全国", None, 2021, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 110.7, "万人", "全国", None, 2022, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 114.8, "万人", "全国", None, 2023, "教育部", _MOE_URL),
    ("研究生录取人数", "postgrad_admit", 130.2, "万人", "全国", None, 2024, "教育部", _MOE_URL),

    # === 4. 公务员报考人数（按年份，国考报名）— 国家统计局，10 条 ===
    ("公务员报考人数", "civil_service", 120.0, "万人", "全国", None, 2015, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 139.0, "万人", "全国", None, 2016, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 148.0, "万人", "全国", None, 2017, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 166.0, "万人", "全国", None, 2018, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 143.0, "万人", "全国", None, 2019, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 143.0, "万人", "全国", None, 2020, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 151.0, "万人", "全国", None, 2021, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 212.0, "万人", "全国", None, 2022, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 250.0, "万人", "全国", None, 2023, "国家统计局", _STATS_URL),
    ("公务员报考人数", "civil_service", 303.0, "万人", "全国", None, 2024, "国家统计局", _STATS_URL),

    # === 5. 城镇就业人数（按年份）— 国家统计局，10 条 ===
    ("城镇就业人数", "employment", 40410.0, "万人", "全国", None, 2015, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 41428.0, "万人", "全国", None, 2016, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 42462.0, "万人", "全国", None, 2017, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 43419.0, "万人", "全国", None, 2018, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 44247.0, "万人", "全国", None, 2019, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 46271.0, "万人", "全国", None, 2020, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 46773.0, "万人", "全国", None, 2021, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 47395.0, "万人", "全国", None, 2022, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 47032.0, "万人", "全国", None, 2023, "国家统计局", _STATS_URL),
    ("城镇就业人数", "employment", 47245.0, "万人", "全国", None, 2024, "国家统计局", _STATS_URL),

    # === 6. 各行业平均工资（2024 年，10 个细分行业）— 国家统计局，10 条 ===
    ("信息传输、软件和信息技术服务业年平均工资", "salary", 234562.0, "元", "全国", "互联网", 2024, "国家统计局", _STATS_URL),
    ("金融业年平均工资", "salary", 197523.0, "元", "全国", "金融", 2024, "国家统计局", _STATS_URL),
    ("科学研究和技术服务业年平均工资", "salary", 171446.0, "元", "全国", "互联网", 2024, "国家统计局", _STATS_URL),
    ("电力、热力、燃气及水生产和供应业年平均工资", "salary", 143592.0, "元", "全国", "能源", 2024, "国家统计局", _STATS_URL),
    ("卫生和社会工作年平均工资", "salary", 132665.0, "元", "全国", "医疗", 2024, "国家统计局", _STATS_URL),
    ("教育业年平均工资", "salary", 122241.0, "元", "全国", "教育", 2024, "国家统计局", _STATS_URL),
    ("文化、体育和娱乐业年平均工资", "salary", 121250.0, "元", "全国", "互联网", 2024, "国家统计局", _STATS_URL),
    ("采矿业年平均工资", "salary", 116243.0, "元", "全国", "能源", 2024, "国家统计局", _STATS_URL),
    ("交通运输、仓储和邮政业年平均工资", "salary", 108534.0, "元", "全国", "物流", 2024, "国家统计局", _STATS_URL),
    ("制造业年平均工资", "salary", 103932.0, "元", "全国", "制造", 2024, "国家统计局", _STATS_URL),
]


@register_crawler
class StatsImporter(BaseCrawler):
    """教育部 / 国家统计局统计数据导入器 — 6 维度 × 10 条 = 60 条预置数据。"""

    name = "stats_importer"
    category = "reports"
    description = "教育部/国家统计局统计数据导入器"

    def fetch(self) -> list[dict]:
        """返回预置的 60 条统计数据原始元组。"""
        return [list(t) for t in _STATS_DATA]

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始元组映射为 MarketData 标准结构。

        字段映射：indicator_name→indicator，indicator_category→category。
        """
        parsed: list[dict] = []
        for r in raw_items:
            (indicator, category, value, unit, region,
             industry, year, source, source_url) = r
            parsed.append({
                "indicator": indicator,        # 对应任务字段 indicator_name
                "category": category,          # 对应任务字段 indicator_category
                "value": value,
                "unit": unit,
                "region": region,
                "industry": industry,
                "year": year,
                "source": source,
                "source_url": source_url,
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """按 indicator + year + region 去重入库，已存在则更新，返回新增条数。"""
        new_count = 0
        for item in items:
            stmt = select(MarketData).where(
                MarketData.indicator == item["indicator"],
                MarketData.year == item["year"],
                MarketData.region == item["region"],
                MarketData.user_id == SYSTEM_USER_ID,
            )
            existing = db.execute(stmt).scalars().first()

            if existing is not None:
                existing.category = item["category"]
                existing.value = item["value"]
                existing.unit = item["unit"]
                existing.industry = item["industry"]
                existing.source = item["source"]
                existing.source_url = item["source_url"]
            else:
                record = MarketData(user_id=SYSTEM_USER_ID, **item)
                db.add(record)
                new_count += 1

        db.commit()
        return new_count
