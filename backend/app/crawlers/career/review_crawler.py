"""公司评价爬虫 — 模拟看准网/脉脉的公司匿名评价数据。

覆盖 20 家知名公司，每公司 4 条评价，共 80 条。
评价涵盖正面/负面/中性三种基调。字段映射到 CompanyReview 表。
"""
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.company import Company, CompanySize
from app.models.company_review import CompanyReview


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

# 评价模板: (基调, 标题池, 内容池, 推荐倾向, 各维度分数范围)
# 维度顺序: work_life_balance, salary_satisfaction, culture_score, career_growth
_POSITIVE_TITLES = ["平台大机会多", "团队氛围好", "福利待遇不错", "技术成长快", "大厂履历有价值"]
_POSITIVE_CONTENTS = [
    "大平台资源丰富，能接触到行业前沿的项目，mentor 制度完善，新人成长很快。",
    "团队技术氛围浓厚，同事都很优秀，code review 严格，能学到很多东西。",
    "福利齐全，有免费三餐和班车，年假充足，加班有调休，整体满意。",
    "晋升通道清晰，绩效评估相对公平，努力会有回报，推荐想拼事业的人来。",
]
_NEUTRAL_TITLES = ["中规中矩的大厂", "稳定但缺乏激情", "看团队", "各有优劣", "适不适合看个人"]
_NEUTRAL_CONTENTS = [
    "工作内容比较常规，稳定但缺乏挑战性，适合追求 work-life balance 的人。",
    "公司体量大流程多，决策慢，但胜在稳定，不会被轻易裁员。",
    "具体体验高度依赖所在团队和直属领导，建议面试时多了解团队情况。",
    "薪资在行业中游水平，福利一般，胜在平台大，跳槽时简历好看。",
]
_NEGATIVE_TITLES = ["加班严重", "晋升通道窄", "管理混乱", "薪资倒挂", "内卷严重"]
_NEGATIVE_CONTENTS = [
    "996 常态化，加班强度大，周末也经常需要响应，身体吃不消。",
    "晋升论资排辈，名额有限，能力强不一定能上，关系比能力重要。",
    "中层管理能力参差不齐，朝令夕改，基层执行疲于奔命。",
    "新人薪资高于老员工，倒挂严重，老员工流失率高。",
    "内卷严重，绩效考核强制分布，同事间竞争大于合作，心理压力大。",
]

# 维度评分范围: (min, max)
_SCORE_RANGES = {
    "positive": {"wlb": (3, 5), "salary": (3, 5), "culture": (4, 5), "growth": (4, 5)},
    "neutral": {"wlb": (3, 4), "salary": (2, 4), "culture": (3, 4), "growth": (2, 4)},
    "negative": {"wlb": (1, 2), "salary": (1, 3), "culture": (1, 3), "growth": (1, 3)},
}


@register_crawler
class ReviewCrawler(BaseCrawler):
    """公司评价爬虫 — 生成 80 条公司评价（20 公司 × 4 条）。"""

    name = "company_review"
    category = "career"
    description = "公司评价爬虫"

    def fetch(self) -> list[dict]:
        """生成 80 条公司评价原始数据（每公司 4 条，混合正面/中性/负面）。"""
        rng = random.Random(42)
        raw: list[dict] = []
        # 每公司的 4 条评价基调：2 正面、1 中性、1 负面
        sentiments_per_company = ["positive", "positive", "neutral", "negative"]
        for company_info in _COMPANIES:
            company_name = company_info[0]
            sentiments = sentiments_per_company.copy()
            rng.shuffle(sentiments)
            used_titles: set[str] = set()
            for sentiment in sentiments:
                if sentiment == "positive":
                    title = rng.choice(_POSITIVE_TITLES)
                    content = rng.choice(_POSITIVE_CONTENTS)
                    ranges = _SCORE_RANGES["positive"]
                    is_recommended = True
                elif sentiment == "neutral":
                    title = rng.choice(_NEUTRAL_TITLES)
                    content = rng.choice(_NEUTRAL_CONTENTS)
                    ranges = _SCORE_RANGES["neutral"]
                    is_recommended = False
                else:
                    title = rng.choice(_NEGATIVE_TITLES)
                    content = rng.choice(_NEGATIVE_CONTENTS)
                    ranges = _SCORE_RANGES["negative"]
                    is_recommended = False
                # 避免同公司标题重复
                if title in used_titles:
                    title = f"{title}（{company_name}）"
                used_titles.add(title)
                rating = rng.randint(ranges["wlb"][0], ranges["wlb"][1] + 1)
                rating = min(max(rating, 1), 5)
                source = rng.choice(["看准网", "脉脉"])
                source_url = f"https://www.kanzhun.com/review/{company_name}/"
                raw.append({
                    "company_name": company_name,
                    "company_info": company_info,
                    "rating": rating,
                    "title": title,
                    "content": content,
                    "is_recommended": is_recommended,
                    "work_life_balance": rng.randint(ranges["wlb"][0], ranges["wlb"][1]),
                    "salary_satisfaction": rng.randint(ranges["salary"][0], ranges["salary"][1]),
                    "culture_score": rng.randint(ranges["culture"][0], ranges["culture"][1]),
                    "career_growth": rng.randint(ranges["growth"][0], ranges["growth"][1]),
                    "source": source,
                    "source_url": source_url,
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 CompanyReview 标准字段。"""
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
                "rating": r["rating"],
                "title": r["title"],
                "content": r["content"],
                "is_recommended": r["is_recommended"],
                "work_life_balance": r["work_life_balance"],
                "salary_satisfaction": r["salary_satisfaction"],
                "culture_score": r["culture_score"],
                "career_growth": r["career_growth"],
                "source": r["source"],
                "source_url": r["source_url"],
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """入库：先确保 Company 记录存在，再写入 CompanyReview。

        去重规则：company + title。
        返回新增评价条数。
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

            # 2. 写入 CompanyReview（去重：user_id + company + title）
            existing_review = db.execute(
                select(CompanyReview).where(
                    CompanyReview.user_id == SYSTEM_USER_ID,
                    CompanyReview.company == item["company"],
                    CompanyReview.title == item["title"],
                )
            ).scalars().first()
            if existing_review is None:
                review = CompanyReview(
                    user_id=SYSTEM_USER_ID,
                    company=item["company"],
                    rating=item["rating"],
                    title=item["title"],
                    content=item["content"],
                    is_recommended=item["is_recommended"],
                    work_life_balance=item["work_life_balance"],
                    salary_satisfaction=item["salary_satisfaction"],
                    culture_score=item["culture_score"],
                    career_growth=item["career_growth"],
                    source=item["source"],
                    source_url=item["source_url"],
                )
                db.add(review)
                new_count += 1

        db.commit()
        return new_count
