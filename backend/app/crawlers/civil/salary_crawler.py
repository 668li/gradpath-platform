"""公务员待遇信息爬虫 — 模拟抓取各地公务员薪资待遇数据。

公务员待遇因地区和级别差异巨大，是岗位选择的重要参考。本爬虫模拟抓取 20 个
城市/地区、4 个级别（科员/副科/正科/副处）的薪资待遇数据，共 80 条记录，
包含基本工资、津贴、年终绩效等综合年收入信息。
"""
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.civil_service_intel import PostIntel

# 系统用户 UUID
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 20 个城市/地区（按待遇水平分档）
# 一线：待遇最高；新一线：待遇中等偏上；二线：待遇中等
_CITIES = [
    "北京", "上海", "广州", "深圳",  # 一线
    "杭州", "南京", "苏州", "成都", "武汉", "西安",  # 新一线
    "重庆", "天津", "青岛", "长沙", "郑州", "合肥", "福州",  # 新一线
    "昆明", "贵阳", "沈阳",  # 二线
]

# 城市分档（1=一线，2=新一线，3=二线）
_CITY_TIER = {
    "北京": 1, "上海": 1, "广州": 1, "深圳": 1,
    "杭州": 2, "南京": 2, "苏州": 2, "成都": 2, "武汉": 2, "西安": 2,
    "重庆": 2, "天津": 2, "青岛": 2, "长沙": 2, "郑州": 2, "合肥": 2, "福州": 2,
    "昆明": 3, "贵阳": 3, "沈阳": 3,
}

# 4 个级别
_LEVELS = ["科员", "副科", "正科", "副处"]

# 各档位各级别的综合年收入区间（单位：万元）
_SALARY_RANGE = {
    1: {"科员": (15, 20), "副科": (20, 25), "正科": (25, 32), "副处": (32, 42)},
    2: {"科员": (10, 14), "副科": (14, 19), "正科": (19, 25), "副处": (25, 32)},
    3: {"科员": (8, 11), "副科": (11, 15), "正科": (15, 20), "副处": (20, 26)},
}

# 各级别对应的工作内容描述
_WORK_CONTENT = {
    "科员": "负责基础业务办理、文件起草、日常事务处理等工作",
    "副科": "负责科室具体业务推进、项目执行、下属指导等工作",
    "正科": "负责科室全面工作、业务统筹、团队管理等工作",
    "副处": "负责处室分管工作、政策制定、跨部门协调等工作",
}

# 各级别对应的晋升速度
_PROMOTION_SPEED = {
    "科员": "medium",
    "副科": "medium",
    "正科": "slow",
    "副处": "slow",
}

# 津贴补贴项
_BONUS_ITEMS = [
    "车补、餐补、年终绩效",
    "车补、餐补、年终绩效、值班补贴",
    "车补、餐补、年终绩效、岗位津贴",
    "车补、餐补、年终绩效、精神文明奖",
]


def _treatment_level(salary_high: int) -> str:
    """根据年收入高值推断待遇水平。"""
    if salary_high >= 30:
        return "high"
    if salary_high >= 18:
        return "medium"
    return "low"


@register_crawler
class SalaryCrawler(BaseCrawler):
    """公务员待遇信息爬虫 — 生成 80 条公务员薪资待遇数据。"""

    name = "civil_salary"
    category = "civil"
    description = "公务员待遇信息爬虫"

    def fetch(self) -> list[dict]:
        """生成 20 城市 × 4 级别共 80 条待遇信息原始数据。"""
        random.seed(42)  # 固定随机种子保证可复现
        raw: list[dict] = []
        for city in _CITIES:
            tier = _CITY_TIER[city]
            for level in _LEVELS:
                low, high = _SALARY_RANGE[tier][level]
                # 在区间内随机取整
                salary_low = random.randint(low, high - 1)
                salary_high = random.randint(salary_low + 1, high)
                raw.append({
                    "region": city,
                    "department": "机关",
                    "post_name": level,
                    "level": level,
                    "salary_low": salary_low,
                    "salary_high": salary_high,
                    "bonus_info": random.choice(_BONUS_ITEMS),
                    "housing_fund": random.choice(["10%", "12%", ""]),
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 PostIntel 标准结构。"""
        parsed: list[dict] = []
        for r in raw_items:
            salary = f"{r['salary_low']}-{r['salary_high']}万/年"
            notes = f"含{r['bonus_info']}，{r['level']}综合年收入约{r['salary_low']}-{r['salary_high']}万"
            bonus_info = r["bonus_info"]
            housing_fund = r["housing_fund"] if r["housing_fund"] else None
            parsed.append({
                "region": r["region"],
                "department": r["department"],
                "post_name": r["post_name"],
                "exam_type": "待遇信息",
                "real_competition": "unknown",
                "treatment_level": _treatment_level(r["salary_high"]),
                "promotion_speed": _PROMOTION_SPEED[r["level"]],
                "workload": "medium",
                "radish_post": "unknown",
                "service_period": "unknown",
                "salary_estimate": salary,
                "housing_fund": housing_fund,
                "bonus_info": bonus_info,
                "department_tier": "待遇参考",
                "work_content": _WORK_CONTENT[r["level"]],
                "insider_notes": notes,
                "risk_warnings": [],
                "data_sources": ["公务员待遇调研", "职级工资标准"],
                "tags": ["待遇", "薪资", r["level"], r["region"]],
                "ai_summary": f"{r['region']}{r['level']}综合年收入{salary}（含{bonus_info}）",
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """按 region + post_name 去重入库，已存在则跳过，返回新增条数。"""
        new_count = 0
        for item in items:
            stmt = select(PostIntel).where(
                PostIntel.region == item["region"],
                PostIntel.post_name == item["post_name"],
                PostIntel.user_id == SYSTEM_USER_ID,
            )
            existing = db.execute(stmt).scalars().first()
            if existing is not None:
                self.stats["duplicates"] += 1
                continue
            record = PostIntel(user_id=SYSTEM_USER_ID, **item)
            db.add(record)
            new_count += 1
        db.commit()
        return new_count
