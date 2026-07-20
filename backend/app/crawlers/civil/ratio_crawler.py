"""考公报录比爬虫 — 模拟从 QZZN 论坛/粉笔网抓取的热门职位历史报录比数据。

报录比是考公岗位选择的核心参考指标。本爬虫模拟抓取 20 个热门职位近 5 年
（2020-2024）的历史报录比数据，共 100 条记录，每条记录包含年份、报名人数、
招录人数、报录比及竞争情况说明。
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

# 20 个热门职位：(region, department, post_name)
_HOT_POSTS = [
    ("北京", "国家税务总局北京市税务局", "一级行政执法员"),
    ("北京", "国家税务总局北京市税务局", "一级科员"),
    ("上海", "国家税务总局上海市税务局", "一级行政执法员"),
    ("广东", "国家税务总局广东省税务局", "一级行政执法员"),
    ("江苏", "国家税务总局江苏省税务局", "一级行政执法员"),
    ("浙江", "国家税务总局浙江省税务局", "一级行政执法员"),
    ("北京", "海关总署北京海关", "海关监管岗科员"),
    ("上海", "海关总署上海海关", "海关监管岗科员"),
    ("广东", "海关总署广州海关", "海关监管岗科员"),
    ("北京", "国家统计局", "数据分析岗科员"),
    ("北京", "审计署", "审计岗科员"),
    ("北京", "财政部", "预算管理岗科员"),
    ("北京", "国家发改委", "综合研究岗科员"),
    ("北京", "中央办公厅", "综合管理岗科员"),
    ("北京", "外交部", "地区业务司科员"),
    ("上海", "上海市发改委", "产业发展岗科员"),
    ("广东", "广东省公安厅", "治安管理岗科员"),
    ("浙江", "浙江省财政厅", "预算管理岗科员"),
    ("江苏", "江苏省财政厅", "财政管理岗科员"),
    ("山东", "山东省财政厅", "预算管理岗科员"),
]

# 历史年份（每职位生成 5 年数据）
_YEARS = [2020, 2021, 2022, 2023, 2024]

# 竞争情况描述模板（按报录比区间）
def _ratio_description(ratio: int) -> str:
    """根据报录比生成竞争情况描述。"""
    if ratio >= 500:
        return "竞争极其激烈"
    if ratio >= 200:
        return "竞争激烈"
    if ratio >= 100:
        return "竞争较高"
    if ratio >= 50:
        return "竞争适中"
    return "竞争相对缓和"


def _competition_level(ratio: int) -> str:
    """根据报录比数值推断竞争激烈程度。"""
    if ratio >= 300:
        return "extreme"
    if ratio >= 100:
        return "high"
    if ratio >= 50:
        return "medium"
    if ratio >= 20:
        return "low"
    return "none"


@register_crawler
class RatioCrawler(BaseCrawler):
    """考公报录比爬虫 — 生成 100 条热门职位历史报录比数据。"""

    name = "civil_ratio"
    category = "civil"
    description = "考公报录比爬虫"

    def fetch(self) -> list[dict]:
        """生成 20 个热门职位 × 5 年共 100 条报录比原始数据。"""
        random.seed(42)  # 固定随机种子保证可复现
        raw: list[dict] = []
        for region, department, post_name in _HOT_POSTS:
            # 每个职位生成 5 年历史数据，报名人数逐年波动
            base_register = random.randint(200, 600)
            for year in _YEARS:
                # 报名人数随年份波动（±30%）
                fluctuation = random.uniform(0.7, 1.3)
                register = max(30, int(base_register * fluctuation))
                hiring = random.randint(1, 5)
                ratio = round(register / hiring)
                desc = _ratio_description(ratio)
                raw.append({
                    "region": region,
                    "department": department,
                    "post_name": post_name,
                    "year": year,
                    "register_count": register,
                    "hiring_count": hiring,
                    "admission_ratio_num": ratio,
                    "description": desc,
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 PostIntel 标准结构。

        notes（insider_notes）包含年份信息，用于按 region + post_name + notes 去重，
        保证同一职位不同年份的记录各自独立。
        """
        parsed: list[dict] = []
        for r in raw_items:
            ratio = r["admission_ratio_num"]
            notes = (
                f"{r['year']}年{r['description']}，报录比 {ratio}:1"
                f"（报名{r['register_count']}人，招录{r['hiring_count']}人）"
            )
            parsed.append({
                "region": r["region"],
                "department": r["department"],
                "post_name": r["post_name"],
                "exam_type": "报录比",
                "real_competition": _competition_level(ratio),
                "treatment_level": "unknown",
                "promotion_speed": "unknown",
                "workload": "unknown",
                "radish_post": "unknown",
                "service_period": "unknown",
                "admission_ratio": f"{ratio}:1",
                "department_tier": "热门职位",
                "work_content": f"{r['department']}{r['post_name']}岗位{r['year']}年度报录情况",
                "insider_notes": notes,
                "risk_warnings": [],
                "data_sources": ["QZZN论坛", "粉笔网"],
                "tags": ["报录比", "历史数据", str(r["year"])],
                "ai_summary": f"{r['department']}{r['post_name']}，{r['year']}年报录比{ratio}:1",
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """按 region + post_name + insider_notes 去重入库，已存在则跳过，返回新增条数。

        notes（insider_notes）包含年份，因此同一职位不同年份的记录不会互相覆盖。
        """
        new_count = 0
        for item in items:
            stmt = select(PostIntel).where(
                PostIntel.region == item["region"],
                PostIntel.post_name == item["post_name"],
                PostIntel.insider_notes == item["insider_notes"],
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
