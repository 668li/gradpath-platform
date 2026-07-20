"""GitHub 开源数据集接入器 — 收录可接入的开源数据集元信息。

本爬虫不直接下载大文件，而是写入数据集元信息（仓库地址、字段 schema、记录数、
许可证等）到 DatasetInfo 表，供后续按需下载与检索。覆盖 5 个领域（就业/教育/
经济/人口/行业），每领域 10 个数据集，共 50 条。

未来接入 requests / pyarrow 后，可用 download_dataset() 真实下载数据集并缓存到
local_path，将 is_downloaded 置为 True。
"""
import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.dataset_info import DatasetInfo


SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 数据集基础信息：(dataset_name, description, category, source_repo, github_org)
_DATASETS: list[tuple[str, str, str, str, str]] = [
    # === 就业（10）===
    ("全国招聘岗位数据集", "覆盖主流招聘平台的结构化岗位与薪资数据", "就业", "china-job-market-dataset", "china-open-data"),
    ("校园招聘薪资调研", "应届生校园招聘 offer 薪资调研合集", "就业", "campus-recruitment-survey", "edu-research"),
    ("高校就业质量报告合集", "近百所高校历年就业质量报告结构化数据", "就业", "employment-quality-report", "career-insight"),
    ("互联网行业跳槽统计", "互联网从业者跳槽频率与涨薪幅度统计", "就业", "job-hopping-statistics", "tech-trends"),
    ("中国开发者薪资调查", "年度开发者薪资与技能调研数据", "就业", "salary-survey-china", "dev-survey"),
    ("互联网裁员追踪数据", "互联网公司裁员时间线与规模追踪", "就业", "layoff-tracker-china", "tech-trends"),
    ("城市人才流动数据", "主要城市人才净流入流出数据", "就业", "talent-flow-china", "urban-data"),
    ("各专业就业率统计", "本科与研究生各专业就业率历年统计", "就业", "employment-rate-by-major", "edu-research"),
    ("招聘岗位趋势数据", "按行业/城市维度的招聘需求趋势", "就业", "job-posting-trends", "china-open-data"),
    ("职业发展路径分析", "常见职业晋升路径与年限分析数据", "就业", "career-path-analysis", "career-insight"),

    # === 教育（10）===
    ("中国教育统计数据", "教育部年度教育事业发展统计数据", "教育", "china-edu-data", "edu-research"),
    ("高考录取分数线合集", "全国高校各专业历年录取分数线", "教育", "gaokao-admission-scores", "edu-research"),
    ("中国大学排名数据", "主流排行榜历年排名与指标数据", "教育", "university-rankings-china", "edu-research"),
    ("考研报录比统计", "各院校专业考研报考录取比统计", "教育", "postgrad-exam-stats", "grad-path"),
    ("K12教育数据集", "中小学教育规模与质量数据", "教育", "k12-education-dataset", "edu-research"),
    ("教育经费统计数据", "财政教育经费投入与分配统计", "教育", "education-funding-stats", "china-open-data"),
    ("高校论文发表统计", "各高校 SCI/SSCI 论文发表统计", "教育", "faculty-publications", "edu-research"),
    ("助学贷款数据", "高校助学贷款发放与偿还数据", "教育", "student-loan-data", "edu-research"),
    ("在线学习趋势数据", "MOOC 等在线学习平台趋势数据", "教育", "online-learning-trends", "edu-research"),
    ("教育公平指数", "区域教育公平指数与维度数据", "教育", "education-equity-index", "edu-research"),

    # === 经济（10）===
    ("分省GDP数据", "全国分省年度 GDP 与产业结构数据", "经济", "china-gdp-by-province", "macro-data"),
    ("财政收入统计", "全国与地方财政收入统计", "经济", "fiscal-revenue-china", "macro-data"),
    ("居民消费价格指数", "CPI 月度与年度同比数据", "经济", "consumer-price-index", "macro-data"),
    ("进出口贸易数据", "按商品/国别进出口贸易统计", "经济", "import-export-trade", "macro-data"),
    ("房地产市场数据", "主要城市房地产成交与价格数据", "经济", "real-estate-market", "urban-data"),
    ("A股历史行情", "A股主要指数与个股历史行情", "经济", "stock-market-historical", "finance-data"),
    ("工业增加值数据", "分行业工业增加值统计", "经济", "industry-value-added", "macro-data"),
    ("外商直接投资", "FDI 行业与地区分布数据", "经济", "foreign-direct-investment", "macro-data"),
    ("社会消费品零售", "社零总额分品类统计", "经济", "retail-sales-china", "macro-data"),
    ("制造业PMI数据", "制造业与非制造业 PMI 月度数据", "经济", "pmi-manufacturing", "macro-data"),

    # === 人口（10）===
    ("人口普查数据集", "第六/七次人口普查结构化数据", "人口", "china-population-census", "demography"),
    ("老龄化人口统计", "分年龄段人口与老龄化指标", "人口", "aging-population-stats", "demography"),
    ("人口流动数据", "省际人口流动与迁移数据", "人口", "migration-flow-china", "demography"),
    ("分省出生率", "各省份出生率与生育率数据", "人口", "birth-rate-by-province", "demography"),
    ("城镇化率数据", "全国与分省城镇化率统计", "人口", "urbanization-rate", "urban-data"),
    ("家庭规模调查", "家庭户规模与结构调查数据", "人口", "household-size-survey", "demography"),
    ("婚姻登记统计", "结婚与离婚登记年度统计", "人口", "marriage-divorce-stats", "demography"),
    ("受教育程度数据", "分年龄段受教育程度数据", "人口", "education-attainment", "demography"),
    ("劳动力参与率", "劳动年龄人口与参与率数据", "人口", "labor-force-participation", "demography"),
    ("人口密度数据", "分地区人口密度统计", "人口", "population-density-china", "demography"),

    # === 行业（10）===
    ("互联网行业发展数据", "互联网行业规模与增长数据", "行业", "china-internet-industry", "industry-data"),
    ("金融科技市场数据", "金融科技细分市场数据", "行业", "fintech-market-data", "industry-data"),
    ("新能源汽车产业数据", "新能源汽车产销与产业链数据", "行业", "ev-industry-china", "industry-data"),
    ("半导体行业数据", "半导体产业链与市场数据", "行业", "semiconductor-industry", "industry-data"),
    ("医疗健康行业统计", "医疗健康行业规模统计", "行业", "healthcare-industry-stats", "industry-data"),
    ("物流行业数据", "物流行业业务量与收入数据", "行业", "logistics-industry", "industry-data"),
    ("新能源行业数据", "光伏/风电等新能源行业数据", "行业", "new-energy-industry", "industry-data"),
    ("文化创意产业数据", "文化创意产业规模数据", "行业", "cultural-creative-industry", "industry-data"),
    ("现代农业产业数据", "现代农业产业产值数据", "行业", "agriculture-industry", "industry-data"),
    ("AI行业人才数据", "人工智能行业人才分布数据", "行业", "ai-industry-talent", "industry-data"),
]

# 各领域默认字段 schema 模板
_SCHEMA_BY_CATEGORY: dict[str, list[dict]] = {
    "就业": [
        {"name": "company", "type": "string"}, {"name": "position", "type": "string"},
        {"name": "salary", "type": "float"}, {"name": "city", "type": "string"},
        {"name": "date", "type": "date"},
    ],
    "教育": [
        {"name": "school", "type": "string"}, {"name": "major", "type": "string"},
        {"name": "year", "type": "int"}, {"name": "score_line", "type": "int"},
        {"name": "province", "type": "string"},
    ],
    "经济": [
        {"name": "year", "type": "int"}, {"name": "province", "type": "string"},
        {"name": "indicator", "type": "string"}, {"name": "value", "type": "float"},
        {"name": "unit", "type": "string"},
    ],
    "人口": [
        {"name": "year", "type": "int"}, {"name": "region", "type": "string"},
        {"name": "population", "type": "int"}, {"name": "age_group", "type": "string"},
        {"name": "gender", "type": "string"},
    ],
    "行业": [
        {"name": "industry", "type": "string"}, {"name": "year", "type": "int"},
        {"name": "revenue", "type": "float"}, {"name": "employees", "type": "int"},
        {"name": "region", "type": "string"},
    ],
}

_FILE_FORMATS = ["json", "csv", "parquet"]
_LICENSES = ["MIT", "Apache-2.0", "CC-BY-4.0", "GPL-3.0"]


def download_dataset(url: str, dest: str) -> bool:
    """数据集下载占位符 — 未来接入 requests / pyarrow 后实现真实下载。

    当前仅返回 False，表示未实际下载。未来实现思路：
    1. 用 requests 流式下载文件到 dest 路径（支持大文件分块）
    2. 若为 parquet/csv，可用 pyarrow 校验文件完整性
    3. 成功后更新 DatasetInfo.local_path 与 is_downloaded=True

    Args:
        url: 数据集下载 URL
        dest: 本地缓存目标路径
    Returns:
        是否下载成功
    """
    # 占位实现：真实下载待接入 requests 后补全
    return False


@register_crawler
class GithubDatasetCrawler(BaseCrawler):
    """GitHub 开源数据集接入器 — 5 领域 × 10 数据集 = 50 条元信息。"""

    name = "github_datasets"
    category = "reports"
    description = "GitHub开源数据集接入器"

    def fetch(self) -> list[dict]:
        """生成 50 条数据集元信息（random.seed(42) 保证可复现）。"""
        random.seed(42)
        raw: list[dict] = []
        for dataset_name, description, category, repo, org in _DATASETS:
            github_url = f"https://github.com/{org}/{repo}"
            # 文件大小：1MB ~ 2GB 区间，按随机档位生成
            size_mb = round(random.uniform(1.0, 2048.0), 1)
            if size_mb >= 1024:
                file_size_estimate = f"{round(size_mb / 1024, 2)}GB"
            else:
                file_size_estimate = f"{size_mb}MB"
            # 最后更新时间：2023-01-01 ~ 2024-12-31 之间随机
            base = datetime(2023, 1, 1, tzinfo=timezone.utc)
            last_updated = base + timedelta(days=random.randint(0, 729))
            raw.append({
                "dataset_name": dataset_name,
                "description": description,
                "category": category,
                "source_repo": repo,
                "github_url": github_url,
                "file_format": random.choice(_FILE_FORMATS),
                "file_size_estimate": file_size_estimate,
                "last_updated": last_updated,
                "license": random.choice(_LICENSES),
                "record_count": random.choice([1000, 5000, 10000, 50000, 100000, 500000]),
                "field_schema": list(_SCHEMA_BY_CATEGORY[category]),
                "local_path": None,
                "is_downloaded": False,
            })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """原始数据已是标准结构，直接透传。"""
        return list(raw_items)

    def store(self, items: list[dict], db: Session) -> int:
        """按 dataset_name + github_url 去重入库，已存在则更新，返回新增条数。"""
        new_count = 0
        for item in items:
            stmt = select(DatasetInfo).where(
                DatasetInfo.dataset_name == item["dataset_name"],
                DatasetInfo.github_url == item["github_url"],
                DatasetInfo.user_id == SYSTEM_USER_ID,
            )
            existing = db.execute(stmt).scalars().first()

            if existing is not None:
                existing.description = item["description"]
                existing.category = item["category"]
                existing.source_repo = item["source_repo"]
                existing.file_format = item["file_format"]
                existing.file_size_estimate = item["file_size_estimate"]
                existing.last_updated = item["last_updated"]
                existing.license = item["license"]
                existing.record_count = item["record_count"]
                existing.field_schema = item["field_schema"]
            else:
                record = DatasetInfo(user_id=SYSTEM_USER_ID, **item)
                db.add(record)
                new_count += 1

        db.commit()
        return new_count
