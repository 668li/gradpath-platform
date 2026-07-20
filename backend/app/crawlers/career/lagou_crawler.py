"""拉勾网招聘岗位爬虫 — 模拟拉勾网平台的招聘信息数据。

拉勾网以互联网/科技岗位为主，本爬虫覆盖 10 个新一线城市，
生成 100 条招聘数据。字段映射到 Company 表与 SalaryBenchmark 表。
"""
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.company import Company, CompanySize
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark


SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 10 个新一线城市（拉勾网偏重新一线）
_CITIES = [
    "杭州", "成都", "南京", "武汉", "西安",
    "苏州", "天津", "重庆", "长沙", "青岛",
]

# 10 个岗位类型: (岗位名, 经验级别, 薪资基线下限 k, 薪资基线上限 k)
_POSITIONS = [
    ("前端开发工程师", ExperienceLevel.junior, 14, 28),
    ("后端开发工程师", ExperienceLevel.mid, 16, 32),
    ("算法工程师", ExperienceLevel.senior, 22, 45),
    ("数据分析师", ExperienceLevel.mid, 14, 28),
    ("产品经理", ExperienceLevel.mid, 16, 32),
    ("UI设计师", ExperienceLevel.junior, 10, 22),
    ("测试工程师", ExperienceLevel.junior, 11, 23),
    ("运维工程师", ExperienceLevel.junior, 13, 28),
    ("运营专员", ExperienceLevel.entry, 7, 16),
    ("销售经理", ExperienceLevel.mid, 9, 22),
]

# 城市薪资系数（新一线普遍略低于一线）
_CITY_MULTIPLIER = {
    "杭州": 1.00, "成都": 0.80, "南京": 0.90, "武汉": 0.78,
    "西安": 0.75, "苏州": 0.85, "天津": 0.78, "重庆": 0.78,
    "长沙": 0.72, "青岛": 0.72,
}

# 公司池: (公司名, 行业, 规模, 阶段, 总部)
# 与 BOSS 爬虫部分重叠，另含若干新公司以扩充数据多样性
_COMPANIES = [
    # 知名互联网公司（与 BOSS 重叠）
    ("腾讯", "互联网", CompanySize.giant, "已上市", "深圳"),
    ("阿里巴巴", "互联网", CompanySize.giant, "已上市", "杭州"),
    ("字节跳动", "互联网", CompanySize.giant, "未上市", "北京"),
    ("美团", "互联网", CompanySize.giant, "已上市", "北京"),
    ("网易", "互联网", CompanySize.giant, "已上市", "杭州"),
    ("快手", "互联网", CompanySize.giant, "已上市", "北京"),
    ("哔哩哔哩", "互联网", CompanySize.large, "已上市", "上海"),
    # 中型互联网/科技公司（拉勾网偏多）
    ("小红书", "互联网", CompanySize.large, "未上市", "上海"),
    ("知乎", "互联网", CompanySize.medium, "已上市", "北京"),
    ("米哈游", "游戏", CompanySize.medium, "未上市", "上海"),
    ("完美世界", "游戏", CompanySize.large, "已上市", "北京"),
    ("莉莉丝游戏", "游戏", CompanySize.medium, "未上市", "上海"),
    ("叠纸游戏", "游戏", CompanySize.small, "未上市", "上海"),
    ("吉比特", "游戏", CompanySize.medium, "已上市", "厦门"),
    ("完美日记", "电商", CompanySize.medium, "已上市", "广州"),
    ("Keep", "互联网", CompanySize.small, "已上市", "北京"),
    ("得到", "互联网", CompanySize.small, "未上市", "北京"),
    ("Vipkid", "教育", CompanySize.medium, "未上市", "北京"),
    ("猿辅导", "教育", CompanySize.large, "未上市", "北京"),
    ("作业帮", "教育", CompanySize.large, "未上市", "北京"),
    ("商汤科技", "人工智能", CompanySize.large, "已上市", "上海"),
    ("地平线", "人工智能", CompanySize.medium, "未上市", "北京"),
    ("第四范式", "人工智能", CompanySize.medium, "已上市", "北京"),
    ("云从科技", "人工智能", CompanySize.small, "已上市", "重庆"),
    ("同花顺", "金融科技", CompanySize.medium, "已上市", "杭州"),
    ("恒生电子", "金融科技", CompanySize.medium, "已上市", "杭州"),
    ("陆金所", "金融科技", CompanySize.large, "已上市", "上海"),
    ("微众银行", "金融科技", CompanySize.large, "未上市", "深圳"),
    ("金山办公", "软件", CompanySize.medium, "已上市", "北京"),
    ("WPS", "软件", CompanySize.medium, "已上市", "北京"),
    ("声网", "互联网", CompanySize.small, "已上市", "上海"),
    ("涂鸦智能", "智能硬件", CompanySize.small, "已上市", "杭州"),
    ("极飞科技", "智能硬件", CompanySize.small, "未上市", "广州"),
    ("优必选", "智能硬件", CompanySize.medium, "已上市", "深圳"),
    ("蔚来", "新能源汽车", CompanySize.large, "已上市", "上海"),
    ("理想汽车", "新能源汽车", CompanySize.large, "已上市", "北京"),
    ("小鹏汽车", "新能源汽车", CompanySize.medium, "已上市", "广州"),
    ("威马汽车", "新能源汽车", CompanySize.small, "未上市", "上海"),
    ("瓜子二手车", "互联网", CompanySize.large, "未上市", "北京"),
    ("货拉拉", "出行", CompanySize.large, "未上市", "深圳"),
]


@register_crawler
class LagouCrawler(BaseCrawler):
    """拉勾网招聘岗位爬虫 — 生成 100 条招聘信息（10 新一线城市 × 10 岗位）。"""

    name = "lagou"
    category = "career"
    description = "拉勾网招聘岗位爬虫"

    def fetch(self) -> list[dict]:
        """生成 100 条招聘信息原始数据（每城市每岗位 1 条）。"""
        random.seed(42)
        raw: list[dict] = []
        for city in _CITIES:
            for position, level, sal_min_k, sal_max_k in _POSITIONS:
                company = random.choice(_COMPANIES)
                multiplier = _CITY_MULTIPLIER.get(city, 1.0)
                # 薪资按城市系数调整（单位：元/月）
                adjusted_min = int(sal_min_k * multiplier * 1000)
                adjusted_max = int(sal_max_k * multiplier * 1000)
                adjusted_median = (adjusted_min + adjusted_max) // 2
                raw.append({
                    "company_name": company[0],
                    "industry": company[1],
                    "size": company[2],
                    "stage": company[3],
                    "headquarters": company[4],
                    "city": city,
                    "position": position,
                    "experience_level": level,
                    "salary_min": adjusted_min,
                    "salary_max": adjusted_max,
                    "salary_median": adjusted_median,
                    "source": "拉勾网",
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """直接透传原始字段（已在 fetch 中结构化）。"""
        return raw_items

    def store(self, items: list[dict], db: Session) -> int:
        """入库：先确保 Company 记录存在，再写入 SalaryBenchmark。

        去重规则：company.name + position + city + experience_level + year。
        返回新增薪资记录条数。
        """
        new_count = 0
        for item in items:
            # 1. 确保 Company 记录存在（按 name 去重）
            existing_company = db.execute(
                select(Company).where(Company.name == item["company_name"])
            ).scalars().first()
            if existing_company is None:
                company = Company(
                    name=item["company_name"],
                    industry=item["industry"],
                    size=item["size"],
                    stage=item["stage"],
                    headquarters=item["headquarters"],
                    description=f"{item['company_name']}是一家位于{item['headquarters']}的{item['industry']}企业。",
                )
                db.add(company)
                db.flush()  # 立即刷新，使后续 select 能查到新公司（autoflush=False 需手动 flush）

            # 2. 写入 SalaryBenchmark（去重：company + position + city + experience_level + year）
            existing_salary = db.execute(
                select(SalaryBenchmark).where(
                    SalaryBenchmark.company == item["company_name"],
                    SalaryBenchmark.position == item["position"],
                    SalaryBenchmark.city == item["city"],
                    SalaryBenchmark.experience_level == item["experience_level"],
                    SalaryBenchmark.year == 2026,
                    SalaryBenchmark.source == "拉勾网",
                )
            ).scalars().first()
            if existing_salary is None:
                salary = SalaryBenchmark(
                    company=item["company_name"],
                    position=item["position"],
                    city=item["city"],
                    experience_level=item["experience_level"],
                    salary_min=item["salary_min"],
                    salary_max=item["salary_max"],
                    salary_median=item["salary_median"],
                    source="拉勾网",
                    year=2026,
                )
                db.add(salary)
                new_count += 1

        db.commit()
        return new_count
