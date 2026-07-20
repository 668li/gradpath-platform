"""BOSS 直聘招聘岗位爬虫 — 模拟 BOSS 直聘平台的招聘信息数据。

BOSS 直聘具有较强的反爬机制，本爬虫使用按真实数据格式整理的预置数据，
覆盖 15 个主要城市的 10 类岗位，生成公司信息与薪资基准数据。
字段映射到 Company 表与 SalaryBenchmark 表。
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

# 25 个城市
_CITIES = [
    "北京", "上海", "深圳", "广州", "杭州", "成都",
    "南京", "武汉", "西安", "苏州", "天津", "重庆",
    "长沙", "青岛", "大连",
    "宁波", "厦门", "福州", "无锡", "合肥",
    "郑州", "沈阳", "哈尔滨", "济南", "南昌",
]

# 10 个岗位类型: (岗位名, 经验级别, 薪资基线下限 k, 薪资基线上限 k)
_POSITIONS = [
    ("前端开发工程师", ExperienceLevel.junior, 15, 30),
    ("后端开发工程师", ExperienceLevel.mid, 18, 35),
    ("算法工程师", ExperienceLevel.senior, 25, 50),
    ("数据分析师", ExperienceLevel.mid, 15, 30),
    ("产品经理", ExperienceLevel.mid, 18, 35),
    ("UI设计师", ExperienceLevel.junior, 12, 25),
    ("测试工程师", ExperienceLevel.junior, 12, 25),
    ("运维工程师", ExperienceLevel.junior, 15, 30),
    ("运营专员", ExperienceLevel.entry, 8, 18),
    ("销售经理", ExperienceLevel.mid, 10, 25),
]

# 城市薪资系数（一线 > 新一线 > 二线）
_CITY_MULTIPLIER = {
    "北京": 1.20, "上海": 1.20, "深圳": 1.20, "杭州": 1.15,
    "广州": 1.00, "成都": 0.90, "南京": 1.00, "武汉": 0.85,
    "西安": 0.85, "苏州": 0.95, "天津": 0.85, "重庆": 0.85,
    "长沙": 0.80, "青岛": 0.80, "大连": 0.80,
    "宁波": 0.85, "厦门": 0.80, "福州": 0.78, "无锡": 0.85,
    "合肥": 0.80, "郑州": 0.78, "沈阳": 0.75, "哈尔滨": 0.72,
    "济南": 0.78, "南昌": 0.72,
}

# 公司池: (公司名, 行业, 规模, 阶段, 总部)
_COMPANIES = [
    # 知名互联网公司
    ("腾讯", "互联网", CompanySize.giant, "已上市", "深圳"),
    ("阿里巴巴", "互联网", CompanySize.giant, "已上市", "杭州"),
    ("字节跳动", "互联网", CompanySize.giant, "未上市", "北京"),
    ("美团", "互联网", CompanySize.giant, "已上市", "北京"),
    ("京东", "电商", CompanySize.giant, "已上市", "北京"),
    ("百度", "互联网", CompanySize.giant, "已上市", "北京"),
    ("小米", "智能硬件", CompanySize.giant, "已上市", "北京"),
    ("华为", "通信", CompanySize.giant, "未上市", "深圳"),
    ("网易", "互联网", CompanySize.giant, "已上市", "杭州"),
    ("拼多多", "电商", CompanySize.giant, "已上市", "上海"),
    ("快手", "互联网", CompanySize.giant, "已上市", "北京"),
    ("哔哩哔哩", "互联网", CompanySize.large, "已上市", "上海"),
    ("滴滴出行", "出行", CompanySize.large, "未上市", "北京"),
    ("携程", "旅游", CompanySize.large, "已上市", "上海"),
    ("新浪", "互联网", CompanySize.large, "已上市", "北京"),
    # 科技/硬件公司
    ("联想", "智能硬件", CompanySize.giant, "已上市", "北京"),
    ("中兴", "通信", CompanySize.giant, "已上市", "深圳"),
    ("海康威视", "智能硬件", CompanySize.giant, "已上市", "杭州"),
    ("大疆", "智能硬件", CompanySize.large, "未上市", "深圳"),
    ("OPPO", "智能硬件", CompanySize.giant, "未上市", "东莞"),
    ("vivo", "智能硬件", CompanySize.giant, "未上市", "东莞"),
    # 人工智能
    ("商汤科技", "人工智能", CompanySize.large, "未上市", "上海"),
    ("旷视科技", "人工智能", CompanySize.medium, "未上市", "北京"),
    ("科大讯飞", "人工智能", CompanySize.giant, "已上市", "合肥"),
    # 金融科技
    ("蚂蚁集团", "金融科技", CompanySize.giant, "未上市", "杭州"),
    ("京东科技", "金融科技", CompanySize.large, "未上市", "北京"),
    ("同花顺", "金融科技", CompanySize.medium, "已上市", "杭州"),
    ("恒生电子", "金融科技", CompanySize.medium, "已上市", "杭州"),
    # 软件/IT 服务
    ("金山办公", "软件", CompanySize.medium, "已上市", "北京"),
    ("用友网络", "软件", CompanySize.large, "已上市", "北京"),
    ("东软集团", "软件", CompanySize.large, "已上市", "沈阳"),
    ("浪潮信息", "服务器", CompanySize.large, "已上市", "济南"),
    ("中科曙光", "服务器", CompanySize.medium, "已上市", "北京"),
    ("神州数码", "IT服务", CompanySize.large, "已上市", "北京"),
    # 智能制造/新能源
    ("海尔智家", "智能硬件", CompanySize.giant, "已上市", "青岛"),
    ("美的集团", "智能硬件", CompanySize.giant, "已上市", "佛山"),
    ("比亚迪", "新能源汽车", CompanySize.giant, "已上市", "深圳"),
    ("宁德时代", "新能源", CompanySize.giant, "已上市", "宁德"),
    ("蔚来", "新能源汽车", CompanySize.large, "已上市", "上海"),
    # 游戏/内容
    ("米哈游", "游戏", CompanySize.medium, "未上市", "上海"),
    ("完美世界", "游戏", CompanySize.large, "已上市", "北京"),
    ("三七互娱", "游戏", CompanySize.large, "已上市", "广州"),
    # 互联网平台
    ("小红书", "互联网", CompanySize.large, "未上市", "上海"),
    ("知乎", "互联网", CompanySize.medium, "已上市", "北京"),
    ("58同城", "互联网", CompanySize.large, "已上市", "北京"),
    ("贝壳找房", "房产", CompanySize.large, "已上市", "北京"),
    ("360", "互联网", CompanySize.large, "已上市", "北京"),
    ("搜狐", "互联网", CompanySize.large, "已上市", "北京"),
    ("欢聚时代", "互联网", CompanySize.large, "已上市", "广州"),
    ("虎牙直播", "互联网", CompanySize.medium, "已上市", "广州"),
    ("汽车之家", "互联网", CompanySize.medium, "已上市", "北京"),
    # === 扩充公司池：旅游/传媒/直播/招聘/房产/物流/电商/零售 ===
    ("同程旅行", "旅游", CompanySize.large, "已上市", "苏州"),
    ("去哪儿网", "旅游", CompanySize.medium, "已上市", "北京"),
    ("马蜂窝", "旅游", CompanySize.medium, "未上市", "北京"),
    ("猫眼娱乐", "传媒", CompanySize.medium, "已上市", "北京"),
    ("快看漫画", "互联网", CompanySize.small, "未上市", "北京"),
    ("虎扑", "互联网", CompanySize.medium, "未上市", "上海"),
    ("斗鱼直播", "互联网", CompanySize.large, "已上市", "武汉"),
    ("映客", "互联网", CompanySize.small, "已上市", "北京"),
    ("探探", "互联网", CompanySize.small, "已上市", "北京"),
    ("陌陌", "互联网", CompanySize.medium, "已上市", "北京"),
    ("BOSS直聘", "互联网", CompanySize.large, "已上市", "北京"),
    ("猎聘", "互联网", CompanySize.medium, "已上市", "北京"),
    ("智联招聘", "互联网", CompanySize.large, "未上市", "北京"),
    ("房多多", "房产", CompanySize.small, "已上市", "上海"),
    ("链家", "房产", CompanySize.large, "未上市", "北京"),
    ("我爱我家", "房产", CompanySize.medium, "已上市", "北京"),
    ("德邦快递", "物流", CompanySize.large, "已上市", "上海"),
    ("安能物流", "物流", CompanySize.large, "未上市", "上海"),
    ("跨境通", "电商", CompanySize.medium, "已上市", "上海"),
    ("有赞", "电商", CompanySize.small, "已上市", "杭州"),
    ("微盟", "电商", CompanySize.small, "已上市", "上海"),
    ("当当网", "电商", CompanySize.medium, "已上市", "北京"),
    ("蘑菇街", "电商", CompanySize.small, "已上市", "杭州"),
    ("唯品会", "电商", CompanySize.giant, "已上市", "广州"),
    ("寺库", "电商", CompanySize.small, "已上市", "北京"),
    ("国美零售", "零售", CompanySize.large, "已上市", "北京"),
    ("苏宁易购", "零售", CompanySize.giant, "已上市", "南京"),
    ("转转", "互联网", CompanySize.medium, "未上市", "北京"),
    ("满帮集团", "物流", CompanySize.large, "已上市", "贵阳"),
    ("滴滴货运", "物流", CompanySize.medium, "未上市", "杭州"),
]


@register_crawler
class BossCrawler(BaseCrawler):
    """BOSS 直聘招聘岗位爬虫 — 生成 150 条招聘信息（15 城市 × 10 岗位）。"""

    name = "boss"
    category = "career"
    description = "BOSS直聘招聘岗位爬虫"

    def fetch(self) -> list[dict]:
        """生成 150 条招聘信息原始数据（每城市每岗位 1 条）。"""
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
                    "source": "BOSS直聘",
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
            # 1. 确保 Company 记录存在（按 name 去重，已存在则跳过）
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
                    SalaryBenchmark.source == "BOSS直聘",
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
                    source="BOSS直聘",
                    year=2026,
                )
                db.add(salary)
                new_count += 1

        db.commit()
        return new_count
