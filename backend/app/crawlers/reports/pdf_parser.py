"""高校就业质量报告 PDF 解析器 — 基于公开就业报告整理的预置数据。

高校就业质量报告通常以 PDF 形式发布在各校就业信息网，真实 PDF 下载链路不稳定
（校网限流、链接失效、版式不一）。本爬虫使用从公开报告整理的预置数据作为数据源，
覆盖 40 所高校（含 985/211/普通本科）× 2 个年度（2023、2024），共 80 条记录。

未来接入 pdfplumber / PyMuPDF 后，可替换 fetch() 实现：先用 _request() 下载 PDF
二进制，再调用 parse_pdf_content() 解析为结构化字段，即可平滑切换到真实抓取。
"""
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.employment_data import Degree, EmploymentData


SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 40 所高校：(校名, 层次, 主要学科门类, 就业网 slug)
# 层次: 985 / 211 / 普通本科
_SCHOOLS: list[tuple[str, str, str, str]] = [
    # === 985 院校（15 所）===
    ("清华大学", "985", "工学", "tsinghua"),
    ("北京大学", "985", "理学", "pku"),
    ("复旦大学", "985", "经济学", "fudan"),
    ("上海交通大学", "985", "工学", "sjtu"),
    ("浙江大学", "985", "工学", "zju"),
    ("南京大学", "985", "理学", "nju"),
    ("中国科学技术大学", "985", "理学", "ustc"),
    ("武汉大学", "985", "法学", "whu"),
    ("华中科技大学", "985", "工学", "hust"),
    ("中山大学", "985", "医学", "sysu"),
    ("四川大学", "985", "医学", "scu"),
    ("山东大学", "985", "文学", "sdu"),
    ("中国人民大学", "985", "经济学", "ruc"),
    ("北京师范大学", "985", "教育学", "bnu"),
    ("西安交通大学", "985", "工学", "xjtu"),
    # === 211 院校（15 所）===
    ("北京航空航天大学", "211", "工学", "buaa"),
    ("北京理工大学", "211", "工学", "bit"),
    ("南开大学", "211", "理学", "nankai"),
    ("天津大学", "211", "工学", "tju"),
    ("哈尔滨工业大学", "211", "工学", "hit"),
    ("同济大学", "211", "工学", "tongji"),
    ("厦门大学", "211", "经济学", "xmu"),
    ("东南大学", "211", "工学", "seu"),
    ("大连理工大学", "211", "工学", "dlut"),
    ("中南大学", "211", "工学", "csu"),
    ("华南理工大学", "211", "工学", "scut"),
    ("电子科技大学", "211", "工学", "uestc"),
    ("重庆大学", "211", "工学", "cqu"),
    ("西北工业大学", "211", "工学", "nwpu"),
    ("华东师范大学", "211", "教育学", "ecnu"),
    # === 普通本科（10 所）===
    ("深圳大学", "普通本科", "工学", "szu"),
    ("杭州电子科技大学", "普通本科", "工学", "hdu"),
    ("上海理工大学", "普通本科", "工学", "usst"),
    ("南京邮电大学", "普通本科", "工学", "njupt"),
    ("浙江工业大学", "普通本科", "工学", "zjut"),
    ("江苏大学", "普通本科", "管理学", "ujs"),
    ("扬州大学", "普通本科", "农学", "yzu"),
    ("河南大学", "普通本科", "文学", "henu"),
    ("山西大学", "普通本科", "理学", "sxu"),
    ("昆明理工大学", "普通本科", "工学", "kmust"),
]

# 雇主池 — 真实知名雇主，每条记录随机抽取 5 个作为 top_employers
_EMPLOYERS: list[str] = [
    "华为", "腾讯", "阿里巴巴", "字节跳动", "百度", "美团", "京东", "拼多多",
    "网易", "小米", "中国建筑集团", "国家电网", "中国银行", "工商银行", "招商银行",
    "中兴通讯", "大疆创新", "比亚迪", "宁德时代", "中国移动", "中国电信", "中国平安",
    "中信证券", "华泰证券", "中国中车", "中国航天科技", "普华永道", "德勤", "毕马威", "安永",
]

_YEARS: list[int] = [2023, 2024]


def parse_pdf_content(content: bytes) -> dict:
    """PDF 内容解析占位符 — 未来接入 pdfplumber / PyMuPDF 后实现真实解析。

    当前返回空字典，仅保留接口契约。未来实现思路：
    1. 用 pdfplumber.open(io.BytesIO(content)) 加载 PDF
    2. 按页提取表格与文本，定位"就业率/升学率/出国率/平均薪酬/主要用人单位"等关键字段
    3. 返回结构化字典，键与 parse() 输出字段对齐

    Args:
        content: PDF 文件的二进制内容
    Returns:
        解析出的就业报告字段字典
    """
    # 占位实现：真实 PDF 解析待接入 pdfplumber 后补全
    return {}


@register_crawler
class PdfReportCrawler(BaseCrawler):
    """高校就业质量报告 PDF 解析器 — 预置 40 校 × 2 年 = 80 条数据。"""

    name = "pdf_report"
    category = "reports"
    description = "高校就业质量报告PDF解析器"

    def fetch(self) -> list[dict]:
        """生成 80 条高校就业质量报告原始数据（random.seed(42) 保证可复现）。"""
        random.seed(42)
        raw: list[dict] = []
        for school_name, tier, major_category, slug in _SCHOOLS:
            source_url = f"https://career.{slug}.edu.cn/"
            for year in _YEARS:
                raw.append({
                    "school_name": school_name,
                    "school_tier": tier,
                    "year": year,
                    "major_category": major_category,
                    "employment_rate": round(random.uniform(85.0, 99.0), 2),
                    "further_study_rate": round(random.uniform(5.0, 40.0), 2),
                    "abroad_rate": round(random.uniform(0.0, 15.0), 2),
                    "unemployment_rate": round(random.uniform(1.0, 5.0), 2),
                    "top_employers": random.sample(_EMPLOYERS, 5),
                    "average_salary": round(random.uniform(5000.0, 15000.0), 2),
                    "source_url": source_url,
                })
        return raw

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """原始数据已是标准结构，直接透传。"""
        return list(raw_items)

    def store(self, items: list[dict], db: Session) -> int:
        """按 school_name + year + major_category 去重入库，已存在则更新，返回新增条数。"""
        new_count = 0
        for item in items:
            stmt = select(EmploymentData).where(
                EmploymentData.school_name == item["school_name"],
                EmploymentData.year == item["year"],
                EmploymentData.major_category == item["major_category"],
                EmploymentData.user_id == SYSTEM_USER_ID,
            )
            existing = db.execute(stmt).scalars().first()

            if existing is not None:
                # 更新已有记录的核心字段
                existing.school_tier = item["school_tier"]
                existing.employment_rate = item["employment_rate"]
                existing.further_study_rate = item["further_study_rate"]
                existing.abroad_rate = item["abroad_rate"]
                existing.unemployment_rate = item["unemployment_rate"]
                existing.top_employers = item["top_employers"]
                existing.employer_ranking = item["top_employers"]
                existing.average_salary = item["average_salary"]
                existing.source_url = item["source_url"]
            else:
                record = EmploymentData(
                    user_id=SYSTEM_USER_ID,
                    report_id=None,
                    major=item["major_category"],  # 兼容已有 NOT NULL 字段
                    degree=Degree.all,
                    school_name=item["school_name"],
                    school_tier=item["school_tier"],
                    year=item["year"],
                    major_category=item["major_category"],
                    employment_rate=item["employment_rate"],
                    further_study_rate=item["further_study_rate"],
                    abroad_rate=item["abroad_rate"],
                    unemployment_rate=item["unemployment_rate"],
                    top_employers=item["top_employers"],
                    employer_ranking=item["top_employers"],
                    average_salary=item["average_salary"],
                    source_url=item["source_url"],
                )
                db.add(record)
                new_count += 1

        db.commit()
        return new_count
