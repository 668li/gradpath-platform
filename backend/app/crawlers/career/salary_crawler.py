"""薪资数据爬虫 — 模拟 OfferShow/Levels.fyi 的薪资数据。

覆盖 20 家公司 × 5 个岗位 × 2 个级别（初级/高级），共 200 条薪资数据。
高级别薪资显著高于初级别，数据偏真实。字段映射到 SalaryBenchmark 表。
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

# 20 家公司: (公司名, 行业, 规模, 阶段, 总部)
_COMPANIES = [
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
    ("360", "互联网", CompanySize.large, "已上市", "北京"),
    ("搜狐", "互联网", CompanySize.large, "已上市", "北京"),
    ("联想", "智能硬件", CompanySize.giant, "已上市", "北京"),
    ("中兴", "通信", CompanySize.giant, "已上市", "深圳"),
    ("海康威视", "智能硬件", CompanySize.giant, "已上市", "杭州"),
    # === 扩充公司池：银行/保险/证券 ===
    ("中国工商银行", "银行", CompanySize.giant, "已上市", "北京"),
    ("中国建设银行", "银行", CompanySize.giant, "已上市", "北京"),
    ("中国银行", "银行", CompanySize.giant, "已上市", "北京"),
    ("中国农业银行", "银行", CompanySize.giant, "已上市", "北京"),
    ("交通银行", "银行", CompanySize.giant, "已上市", "上海"),
    ("招商银行", "银行", CompanySize.giant, "已上市", "深圳"),
    ("中国平安", "保险", CompanySize.giant, "已上市", "深圳"),
    ("中国人寿", "保险", CompanySize.giant, "已上市", "北京"),
    ("广发证券", "证券", CompanySize.large, "已上市", "广州"),
    ("泰康人寿", "保险", CompanySize.large, "未上市", "北京"),
    # === 教育 ===
    ("好未来", "教育", CompanySize.large, "已上市", "北京"),
    ("新东方", "教育", CompanySize.giant, "已上市", "北京"),
    ("高途课堂", "教育", CompanySize.medium, "已上市", "北京"),
    ("网易有道", "教育", CompanySize.medium, "已上市", "杭州"),
    ("一起教育", "教育", CompanySize.small, "已上市", "北京"),
    # === 医疗/医药 ===
    ("药明康德", "医药", CompanySize.giant, "已上市", "上海"),
    ("恒瑞医药", "医药", CompanySize.giant, "已上市", "连云港"),
    ("迈瑞医疗", "医疗器械", CompanySize.giant, "已上市", "深圳"),
    ("联影医疗", "医疗器械", CompanySize.large, "已上市", "上海"),
    ("微医", "医疗", CompanySize.medium, "未上市", "杭州"),
    ("平安好医生", "医疗", CompanySize.medium, "已上市", "深圳"),
    ("华大基因", "医疗", CompanySize.large, "已上市", "深圳"),
    ("金域医学", "医疗", CompanySize.large, "已上市", "广州"),
    ("京东健康", "医疗", CompanySize.large, "已上市", "北京"),
    ("阿里健康", "医疗", CompanySize.large, "已上市", "杭州"),
    ("美年健康", "医疗", CompanySize.large, "已上市", "上海"),
    ("爱尔眼科", "医疗", CompanySize.giant, "已上市", "长沙"),
    # === 智能硬件/家电 ===
    ("格力电器", "智能硬件", CompanySize.giant, "已上市", "珠海"),
    ("TCL科技", "智能硬件", CompanySize.giant, "已上市", "惠州"),
    ("海信集团", "智能硬件", CompanySize.giant, "已上市", "青岛"),
    ("长虹", "智能硬件", CompanySize.large, "已上市", "绵阳"),
    ("康佳", "智能硬件", CompanySize.medium, "已上市", "深圳"),
    ("创维", "智能硬件", CompanySize.large, "已上市", "深圳"),
    # === 汽车 ===
    ("长城汽车", "新能源汽车", CompanySize.giant, "已上市", "保定"),
    ("吉利汽车", "新能源汽车", CompanySize.giant, "已上市", "杭州"),
    ("广汽集团", "汽车", CompanySize.giant, "已上市", "广州"),
    ("上汽集团", "汽车", CompanySize.giant, "已上市", "上海"),
    ("一汽集团", "汽车", CompanySize.giant, "未上市", "长春"),
    # === 新能源 ===
    ("隆基绿能", "新能源", CompanySize.giant, "已上市", "西安"),
    ("阳光电源", "新能源", CompanySize.large, "已上市", "合肥"),
    ("通威股份", "新能源", CompanySize.giant, "已上市", "成都"),
    ("天合光能", "新能源", CompanySize.large, "已上市", "常州"),
    ("晶澳科技", "新能源", CompanySize.large, "已上市", "北京"),
    # === 房地产 ===
    ("万科", "房产", CompanySize.giant, "已上市", "深圳"),
    ("碧桂园", "房产", CompanySize.giant, "已上市", "佛山"),
    ("保利发展", "房产", CompanySize.giant, "已上市", "广州"),
    ("华润置地", "房产", CompanySize.giant, "已上市", "深圳"),
    ("龙湖集团", "房产", CompanySize.large, "已上市", "北京"),
    # === 传媒/内容 ===
    ("阅文集团", "互联网", CompanySize.medium, "已上市", "上海"),
    ("芒果超媒", "传媒", CompanySize.large, "已上市", "长沙"),
    ("东方明珠", "传媒", CompanySize.large, "已上市", "上海"),
    ("华策影视", "传媒", CompanySize.medium, "已上市", "杭州"),
    # === 物流 ===
    ("顺丰控股", "物流", CompanySize.giant, "已上市", "深圳"),
    ("中通快递", "物流", CompanySize.large, "已上市", "上海"),
    ("圆通速递", "物流", CompanySize.large, "已上市", "上海"),
    ("韵达股份", "物流", CompanySize.large, "已上市", "上海"),
    ("申通快递", "物流", CompanySize.medium, "已上市", "上海"),
    # === 零售 ===
    ("永辉超市", "零售", CompanySize.large, "已上市", "福州"),
    ("居然之家", "零售", CompanySize.large, "已上市", "北京"),
    ("红星美凯龙", "零售", CompanySize.large, "已上市", "上海"),
    ("中国中免", "零售", CompanySize.giant, "已上市", "北京"),
    # === 半导体 ===
    ("中芯国际", "半导体", CompanySize.giant, "已上市", "上海"),
    ("韦尔股份", "半导体", CompanySize.large, "已上市", "上海"),
    ("兆易创新", "半导体", CompanySize.medium, "已上市", "北京"),
    ("紫光国微", "半导体", CompanySize.medium, "已上市", "北京"),
    ("长电科技", "半导体", CompanySize.large, "已上市", "无锡"),
    ("华天科技", "半导体", CompanySize.large, "已上市", "天水"),
    ("京东方", "半导体", CompanySize.giant, "已上市", "北京"),
    ("三安光电", "半导体", CompanySize.giant, "已上市", "厦门"),
    ("北方华创", "半导体", CompanySize.large, "已上市", "北京"),
    ("中微公司", "半导体", CompanySize.medium, "已上市", "上海"),
    # === 通信 ===
    ("中国移动", "通信", CompanySize.giant, "已上市", "北京"),
    ("中国电信", "通信", CompanySize.giant, "已上市", "北京"),
    ("中国联通", "通信", CompanySize.giant, "已上市", "北京"),
    # === 云计算/软件 ===
    ("金山云", "云计算", CompanySize.medium, "已上市", "北京"),
    ("UCloud", "云计算", CompanySize.small, "已上市", "上海"),
    ("青云科技", "云计算", CompanySize.small, "已上市", "北京"),
    ("宝信软件", "软件", CompanySize.large, "已上市", "上海"),
    ("太极股份", "软件", CompanySize.large, "已上市", "北京"),
    # === 食品 ===
    ("海天味业", "食品", CompanySize.giant, "已上市", "佛山"),
    ("伊利股份", "食品", CompanySize.giant, "已上市", "呼和浩特"),
    ("蒙牛乳业", "食品", CompanySize.giant, "已上市", "呼和浩特"),
    ("双汇发展", "食品", CompanySize.large, "已上市", "漯河"),
    ("东鹏特饮", "食品", CompanySize.medium, "已上市", "深圳"),
    # === 酒店 ===
    ("锦江酒店", "酒店", CompanySize.giant, "已上市", "上海"),
    ("华住集团", "酒店", CompanySize.giant, "已上市", "上海"),
    ("首旅酒店", "酒店", CompanySize.large, "已上市", "北京"),
    # === 基建/重工 ===
    ("中国中车", "制造", CompanySize.giant, "已上市", "北京"),
    ("中国铁建", "基建", CompanySize.giant, "已上市", "北京"),
    ("中国中铁", "基建", CompanySize.giant, "已上市", "北京"),
    ("中国建筑", "基建", CompanySize.giant, "已上市", "北京"),
    ("中国交建", "基建", CompanySize.giant, "已上市", "北京"),
    ("三一重工", "制造", CompanySize.giant, "已上市", "长沙"),
    ("中联重科", "制造", CompanySize.giant, "已上市", "长沙"),
    ("徐工机械", "制造", CompanySize.giant, "已上市", "徐州"),
    ("潍柴动力", "制造", CompanySize.giant, "已上市", "潍坊"),
    # === 能源 ===
    ("中国石化", "能源", CompanySize.giant, "已上市", "北京"),
    ("中国石油", "能源", CompanySize.giant, "已上市", "北京"),
    ("中国海洋石油", "能源", CompanySize.giant, "已上市", "北京"),
    ("国家电网", "能源", CompanySize.giant, "未上市", "北京"),
    ("南方电网", "能源", CompanySize.giant, "未上市", "广州"),
]

# 5 个岗位 × 2 个级别: (岗位名, 经验级别, 薪资下限 k, 薪资上限 k)
# 高级别薪资显著高于初级别
_POSITION_LEVELS = [
    # 初级
    ("前端开发工程师", ExperienceLevel.entry, 12, 20),
    ("后端开发工程师", ExperienceLevel.entry, 15, 25),
    ("算法工程师", ExperienceLevel.entry, 20, 35),
    ("产品经理", ExperienceLevel.entry, 12, 22),
    ("测试工程师", ExperienceLevel.entry, 10, 18),
    # 高级
    ("前端开发工程师", ExperienceLevel.senior, 25, 45),
    ("后端开发工程师", ExperienceLevel.senior, 30, 55),
    ("算法工程师", ExperienceLevel.senior, 40, 70),
    ("产品经理", ExperienceLevel.senior, 25, 45),
    ("测试工程师", ExperienceLevel.senior, 20, 35),
]

# 数据来源
_SOURCES = ["OfferShow", "Levels.fyi"]


@register_crawler
class SalaryCrawler(BaseCrawler):
    """薪资数据爬虫 — 生成 200 条薪资数据（20 公司 × 5 岗位 × 2 级别）。"""

    name = "salary_data"
    category = "career"
    description = "薪资数据爬虫"

    def fetch(self) -> list[dict]:
        """生成 200 条薪资数据原始数据。"""
        rng = random.Random(42)
        raw: list[dict] = []
        for company_info in _COMPANIES:
            company_name = company_info[0]
            city = company_info[4]  # 总部城市
            for position, level, sal_min_k, sal_max_k in _POSITION_LEVELS:
                # 在基线范围内随机波动 ±15%，模拟真实薪资分布
                jitter = rng.uniform(0.85, 1.15)
                adjusted_min = int(sal_min_k * jitter * 1000)
                adjusted_max = int(sal_max_k * jitter * 1000)
                adjusted_median = (adjusted_min + adjusted_max) // 2
                source = rng.choice(_SOURCES)
                raw.append({
                    "company_name": company_name,
                    "company_info": company_info,
                    "city": city,
                    "position": position,
                    "experience_level": level,
                    "salary_min": adjusted_min,
                    "salary_max": adjusted_max,
                    "salary_median": adjusted_median,
                    "source": source,
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 SalaryBenchmark 标准字段。"""
        parsed: list[dict] = []
        for r in raw_items:
            info = r["company_info"]
            parsed.append({
                "company_name": r["company_name"],
                "industry": info[1],
                "size": info[2],
                "stage": info[3],
                "headquarters": info[4],
                "company": r["company_name"],
                "city": r["city"],
                "position": r["position"],
                "experience_level": r["experience_level"],
                "salary_min": r["salary_min"],
                "salary_max": r["salary_max"],
                "salary_median": r["salary_median"],
                "source": r["source"],
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """入库：先确保 Company 记录存在，再写入 SalaryBenchmark。

        去重规则：company + position + experience_level + city。
        返回新增薪资记录条数。
        """
        new_count = 0
        for item in items:
            # 1. 确保 Company 记录存在
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

            # 2. 写入 SalaryBenchmark（去重：company + position + experience_level + city）
            existing_salary = db.execute(
                select(SalaryBenchmark).where(
                    SalaryBenchmark.company == item["company"],
                    SalaryBenchmark.position == item["position"],
                    SalaryBenchmark.experience_level == item["experience_level"],
                    SalaryBenchmark.city == item["city"],
                )
            ).scalars().first()
            if existing_salary is None:
                salary = SalaryBenchmark(
                    company=item["company"],
                    position=item["position"],
                    city=item["city"],
                    experience_level=item["experience_level"],
                    salary_min=item["salary_min"],
                    salary_max=item["salary_max"],
                    salary_median=item["salary_median"],
                    source=item["source"],
                    year=2026,
                )
                db.add(salary)
                new_count += 1

        db.commit()
        return new_count
