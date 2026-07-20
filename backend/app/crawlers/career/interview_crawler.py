"""面试经验爬虫 — 模拟看准网/牛客网的面试经验帖数据。

覆盖 20 家知名公司的面试经验，每公司 6 条，共 120 条。
字段映射到 InterviewReport 表。InterviewReport 表有唯一约束
(user_id, company, position, interview_year)，因此每公司的 6 条
面试经验使用不同岗位以保证不冲突。
"""
import random
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.company import Company, CompanySize
from app.models.interview_report import InterviewReport, InterviewResult


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
]

# 候选岗位池（每公司从中取 6 个不同岗位，避免唯一约束冲突）
_POSITIONS = [
    "前端开发工程师", "后端开发工程师", "算法工程师", "数据分析师",
    "产品经理", "UI设计师", "测试工程师", "运维工程师",
    "运营专员", "销售经理",
]

# 面试题类型池
_QUESTION_TYPES = [
    "自我介绍", "项目经验深挖", "算法题（手撕代码）", "系统设计",
    "八股文基础", "数据库设计", "HR面试", "反问环节",
    "职业规划", "情景题", "智力题", "技术架构讨论",
]

# 面试感受模板（按结果分类）
_EXPERIENCE_TEMPLATES = {
    InterviewResult.offer: [
        "面试官专业且友善，问题有深度但不刁钻，整体体验很好。HR反馈也很及时，{days}天就拿到了offer。",
        "流程规范，{rounds}轮面试安排紧凑，面试官对项目经验问得很细，准备充分的话不难通过。",
        "技术面侧重基础和项目，面试官会引导思考，整体氛围轻松，是对自己能力的一次很好检验。",
    ],
    InterviewResult.rejected: [
        "面试难度较大，算法题没完全做出来，面试官比较严肃，最终未通过。建议重点复习数据结构与算法。",
        "问题偏深，项目经验被反复追问细节，准备不充分。面试官水平很高，能发现知识盲区。",
        "系统设计环节表现不佳，对分布式场景不够熟悉，面试官追问较多，最终未能通过。",
    ],
    InterviewResult.pending: [
        "技术面已通过，还在等HR面安排，HR说一周内给回复，期待中。",
        "面试流程较长，已完成{rounds}轮，仍在等结果，整体体验尚可。",
        "笔试和初面都过了，正在等终面通知，据说是高管面，有点紧张。",
    ],
}


def _random_recent_date(rng: random.Random, today: date) -> date:
    """生成最近 6 个月内的随机日期。"""
    days_ago = rng.randint(7, 180)
    return today - timedelta(days=days_ago)


@register_crawler
class InterviewCrawler(BaseCrawler):
    """面试经验爬虫 — 生成 120 条面试经验（20 公司 × 6 条）。"""

    name = "interview"
    category = "career"
    description = "面试经验爬虫"

    def fetch(self) -> list[dict]:
        """生成 120 条面试经验原始数据。"""
        rng = random.Random(42)
        today = date(2026, 7, 3)
        raw: list[dict] = []
        for company_info in _COMPANIES:
            company_name = company_info[0]
            # 每公司取 6 个不同岗位（保证唯一约束不冲突）
            positions = rng.sample(_POSITIONS, 6)
            for position in positions:
                interview_date = _random_recent_date(rng, today)
                difficulty = rng.randint(2, 5)
                result = rng.choices(
                    [InterviewResult.offer, InterviewResult.rejected, InterviewResult.pending],
                    weights=[45, 35, 20],
                )[0]
                rounds = rng.randint(2, 5)
                # 随机选 3-5 个面试题类型
                questions = rng.sample(_QUESTION_TYPES, rng.randint(3, 5))
                template = rng.choice(_EXPERIENCE_TEMPLATES[result])
                experience = template.format(rounds=rounds, days=rng.randint(2, 7))
                source_url = f"https://www.kanzhun.com/interview/{company_name}/{position}/"
                raw.append({
                    "company_name": company_name,
                    "company_info": company_info,
                    "position": position,
                    "interview_date": interview_date,
                    "interview_year": interview_date.year,
                    "difficulty": difficulty,
                    "result": result,
                    "rounds": rounds,
                    "questions": questions,
                    "experience": experience,
                    "source_url": source_url,
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 InterviewReport 标准字段。"""
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
                "position": r["position"],
                "city": info[4],
                "interview_year": r["interview_year"],
                "difficulty": r["difficulty"],
                "result": r["result"],
                "rounds": r["rounds"],
                "dimensions": r["questions"],
                "summary": f"【面试日期】{r['interview_date'].isoformat()}\n【面试感受】{r['experience']}\n【来源】{r['source_url']}",
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """入库：先确保 Company 记录存在，再写入 InterviewReport。

        去重规则：company + position + interview_year（受表唯一约束保护）。
        返回新增面试经验条数。
        """
        new_count = 0
        for item in items:
            # 1. 确保 Company 记录存在（若公司不存在则创建）
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

            # 2. 写入 InterviewReport（去重：user_id + company + position + interview_year）
            existing_report = db.execute(
                select(InterviewReport).where(
                    InterviewReport.user_id == SYSTEM_USER_ID,
                    InterviewReport.company == item["company"],
                    InterviewReport.position == item["position"],
                    InterviewReport.interview_year == item["interview_year"],
                )
            ).scalars().first()
            if existing_report is None:
                report = InterviewReport(
                    user_id=SYSTEM_USER_ID,
                    company=item["company"],
                    position=item["position"],
                    city=item["city"],
                    interview_year=item["interview_year"],
                    rounds=item["rounds"],
                    result=item["result"],
                    dimensions=item["dimensions"],
                    difficulty=item["difficulty"],
                    summary=item["summary"],
                )
                db.add(report)
                new_count += 1

        db.commit()
        return new_count
