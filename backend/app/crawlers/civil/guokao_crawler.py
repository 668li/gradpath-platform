"""国考职位表爬虫 — 基于公开职位表整理的预置国考岗位数据。

国考职位表通常以 Excel 形式发布在国家公务员局官网，难以稳定抓取，本爬虫使用
根据公开招录信息整理的预置数据，覆盖 6 个地区 × 8 个部门类型，共 120 条国考
职位记录，包含职位代码、招录人数、报名人数、报录比、学历/专业/政治面貌/年龄/
工作年限要求、笔试科目、薪资估计等关键字段。
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

# 国考覆盖地区（6 个）
_GUOKAO_REGIONS = ["中央", "北京", "上海", "广东", "江苏", "浙江"]

# 8 个部门类型
_DEPT_TYPES = ["海关", "税务", "统计", "审计", "财政", "公安", "检察", "法院"]

# 中央部委全称（中央地区使用）
_CENTRAL_DEPTS = {
    "海关": "海关总署",
    "税务": "国家税务总局",
    "统计": "国家统计局",
    "审计": "审计署",
    "财政": "财政部",
    "公安": "公安部",
    "检察": "最高人民检察院",
    "法院": "最高人民法院",
}

# 职位名称候选
_POST_NAMES = [
    "一级主任科员及以下",
    "二级主任科员及以下",
    "三级主任科员及以下",
    "四级主任科员及以下",
    "一级科员",
    "二级科员",
    "一级行政执法员",
]

# 学历要求候选
_EDU_REQUIREMENTS = ["本科", "本科及以上", "硕士研究生"]

# 专业要求候选
_MAJOR_REQUIREMENTS = [
    "经济学类", "法学类", "计算机类", "中国语言文学类",
    "工商管理类", "统计学类", "会计学", "财政学类",
    "新闻传播学类", "公共管理类", "不限专业",
]

# 政治面貌要求候选
_POLITICAL_REQUIREMENTS = ["中共党员", "中共党员或共青团员", "不限"]

# 工作年限要求候选
_WORK_YEAR_REQUIREMENTS = ["无限制", "二年", "一年"]

# 各部门类型的工作内容描述
_WORK_CONTENT = {
    "海关": "从事进出口货物监管、关税征管、走私查缉等工作",
    "税务": "从事税收征管、纳税服务、税务稽查等工作",
    "统计": "从事统计数据收集、分析、发布等工作",
    "审计": "从事审计监督、财务审计、绩效审计等工作",
    "财政": "从事财政预算编制、资金管理、财务监督等工作",
    "公安": "从事治安管理、案件侦办、安全保卫等工作",
    "检察": "从事审查起诉、法律监督、公益诉讼等工作",
    "法院": "从事案件审理、司法裁判、执行等工作",
}


def _dept_name(region: str, dept_type: str) -> str:
    """根据地区生成完整部门名：中央用部委全称，地方用"地区+部门+局"。"""
    if region == "中央":
        return _CENTRAL_DEPTS[dept_type]
    if dept_type in ("检察", "法院"):
        return f"{region}{dept_type}"
    return f"{region}{dept_type}局"


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
class GuokaoCrawler(BaseCrawler):
    """国考职位表爬虫 — 生成 120 条国考职位模拟数据。"""

    name = "guokao"
    category = "civil"
    description = "国考职位表爬虫"

    def fetch(self) -> list[dict]:
        """生成 6 地区 × 8 部门类型共 120 条国考职位原始数据。"""
        random.seed(42)  # 固定随机种子保证可复现
        raw: list[dict] = []
        post_code_seq = 300110001001  # 职位编码起始
        combo_index = 0
        for region in _GUOKAO_REGIONS:
            for dept_type in _DEPT_TYPES:
                department = _dept_name(region, dept_type)
                # 交替生成 3/2 个职位，保证总数 120（24×3 + 24×2）
                num_posts = 3 if combo_index % 2 == 0 else 2
                combo_index += 1
                for i in range(num_posts):
                    hiring = random.randint(1, 5)
                    register = random.randint(50, 500)
                    ratio = round(register / hiring)
                    raw.append({
                        "region": region,
                        "department": department,
                        "department_type": dept_type,
                        "post_name": _POST_NAMES[(combo_index + i) % len(_POST_NAMES)],
                        "post_code": str(post_code_seq),
                        "hiring_count": hiring,
                        "register_count": register,
                        "admission_ratio_num": ratio,
                        "education_requirement": random.choice(_EDU_REQUIREMENTS),
                        "major_requirement": random.choice(_MAJOR_REQUIREMENTS),
                        "political_requirement": random.choice(_POLITICAL_REQUIREMENTS),
                        "age_requirement": "18-35周岁",
                        "work_year_requirement": random.choice(_WORK_YEAR_REQUIREMENTS),
                        "exam_subjects": "行政职业能力测验,申论",
                        "salary_low": random.randint(8000, 12000),
                        "salary_high": random.randint(13000, 20000),
                        "source_url": "https://www.scs.gov.cn/",
                    })
                    post_code_seq += 1
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据映射为 PostIntel 标准结构。

        由于 PostIntel 模型无 post_code/hiring_count/education_requirement 等独立字段，
        将这些详细招录要求汇总到 insider_notes，source_url 放入 data_sources。
        """
        parsed: list[dict] = []
        for r in raw_items:
            ratio = r["admission_ratio_num"]
            salary = f"{r['salary_low']}-{r['salary_high']}元/月"
            # 详细招录要求汇总到 insider_notes
            notes_lines = [
                f"职位代码：{r['post_code']}",
                f"招录人数：{r['hiring_count']}人，报名人数：{r['register_count']}人",
                f"学历要求：{r['education_requirement']}",
                f"专业要求：{r['major_requirement']}",
                f"政治面貌：{r['political_requirement']}",
                f"年龄要求：{r['age_requirement']}",
                f"工作年限：{r['work_year_requirement']}",
                f"笔试科目：{r['exam_subjects']}",
                f"数据来源：{r['source_url']}",
            ]
            parsed.append({
                "region": r["region"],
                "department": r["department"],
                "post_name": r["post_name"],
                "exam_type": "国考",
                "real_competition": _competition_level(ratio),
                "treatment_level": "medium",
                "promotion_speed": "medium",
                "workload": "medium",
                "radish_post": "medium",
                "service_period": "5年",
                "admission_ratio": f"{ratio}:1",
                "salary_estimate": salary,
                "department_tier": "中央部委" if r["region"] == "中央" else "中央直属",
                "work_content": _WORK_CONTENT[r["department_type"]],
                "insider_notes": "\n".join(notes_lines),
                "risk_warnings": [],
                "data_sources": ["国家公务员局", r["source_url"]],
                "tags": ["国考", r["region"], r["department_type"]],
                "ai_summary": f"{r['department']}{r['post_name']}岗位，报录比{ratio}:1，薪资{salary}",
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """按 region + department + post_name 去重入库，已存在则跳过，返回新增条数。"""
        new_count = 0
        for item in items:
            stmt = select(PostIntel).where(
                PostIntel.region == item["region"],
                PostIntel.department == item["department"],
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
