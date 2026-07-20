# backend/pipeline/extractor.py
"""LLM 辅助就业报告解析器"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.employment_data import Degree, EmploymentData
from app.models.report_record import ParseStatus, ReportRecord
from app.services.ai_orchestrator import AIOrchestrator
from pipeline.extractors.html_extractor import extract_html

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_report.txt"
MAX_TEXT_LENGTH = 12000  # LLM 输入文本上限

# 统一编排层：复用 AIOrchestrator 的超时/重试语义，保留原 call_llm 的 60s 超时
LLM_TIMEOUT = 60

try:
    _PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")
except Exception as e:
    logger.error(f"加载 prompt 模板失败: {e}")
    _PROMPT_TEMPLATE = ""


async def extract_report(db: Session, report_id: UUID) -> ReportRecord | None:
    """解析报告，通过 LLM 提取结构化就业数据。

    Args:
        db: 数据库会话
        report_id: ReportRecord 的 ID

    Returns:
        更新后的 ReportRecord，或 None（报告不存在或无 raw_html 内容时）
    """
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        return None

    if not report.raw_html:
        report.parse_status = ParseStatus.failed
        report.parse_error = "无 raw_html 内容"
        db.commit()
        return None

    # 清洗 HTML 为纯文本
    text = _clean_html(report.raw_html)
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    # 调用 LLM
    try:
        llm_response = await call_llm(text)
        data = json.loads(llm_response)
    except json.JSONDecodeError as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 返回无效 JSON: {e}"
        db.commit()
        return report
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 调用失败: {e}"
        db.commit()
        return report

    # 写入 EmploymentData
    majors = data.get("majors", [])
    # 解析幂等：先清除该 report 已有的 EmploymentData，避免重复解析产生残留数据
    db.query(EmploymentData).filter(EmploymentData.report_id == report.id).delete()
    for major_data in majors:
        # 单个专业的解析失败（如非法 degree 值）应跳过该专业并记录警告，
        # 不影响其他专业与整份报告的解析结果
        try:
            emp = EmploymentData(
                report_id=report.id,
                major=major_data.get("major", "未知专业"),
                degree=Degree(major_data.get("degree", "all")),
                total_graduates=major_data.get("total_graduates"),
                employment_rate=major_data.get("employment_rate"),
                further_study_rate=major_data.get("further_study_rate"),
                civil_service_rate=major_data.get("civil_service_rate"),
                abroad_rate=major_data.get("abroad_rate"),
                startup_rate=major_data.get("startup_rate"),
                gap_year_rate=major_data.get("gap_year_rate"),
                employer_ranking=major_data.get("employer_ranking", []),
                industry_distribution=major_data.get("industry_distribution", {}),
                destination_region=major_data.get("destination_region", {}),
                school_for_further_study=major_data.get("school_for_further_study", []),
            )
            db.add(emp)
        except Exception as e:
            logger.warning(
                "跳过专业 %r 解析（report_id=%s）: %s",
                major_data.get("major"),
                report.id,
                e,
            )
            continue

    report.parse_status = ParseStatus.parsed
    report.parsed_at = datetime.now(timezone.utc)
    report.parse_error = None
    db.commit()
    return report


def _clean_html(html: str) -> str:
    """将 HTML 清洗为纯文本（委托给 html_extractor）。"""
    return extract_html(html).text


async def call_llm(report_text: str) -> str:
    """调用 LLM API 解析报告文本，返回 JSON 字符串。

    通过统一编排层 AIOrchestrator 发起调用（等价于原 httpx.POST 通道），
    保留原 call_llm 的 60s 超时语义。prompt 模板整体作为 user_prompt 传入，
    保持与原实现一致的请求内容。
    """
    if not _PROMPT_TEMPLATE:
        raise ValueError("prompt 模板未加载")
    prompt = _PROMPT_TEMPLATE.replace("{report_text}", report_text)

    orchestrator = AIOrchestrator()
    return await orchestrator.chat(system_prompt="", user_prompt=prompt, timeout=LLM_TIMEOUT)
