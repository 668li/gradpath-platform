# backend/pipeline/fetcher.py
"""高校就业质量报告抓取器"""
import time
import re
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy.orm import Session

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus

USER_AGENT = "GradPathBot/1.0 (career research; +https://github.com/gradpath)"
REQUEST_DELAY = 3  # 秒，请求间隔
TIMEOUT = 30
MAX_RETRIES = 3


def check_robots_allowed(url: str) -> bool:
    """检查 robots.txt 是否允许抓取"""
    try:
        rp = RobotFileParser()
        rp.set_url(url + "/robots.txt" if not url.endswith("/") else url + "robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True  # 无法读取 robots.txt 时默认允许


def fetch_report(
    db: Session,
    school_slug: str,
    year: int,
    direct_url: str | None = None,
) -> ReportRecord | None:
    """抓取指定学校的指定年份就业质量报告。

    Args:
        db: 数据库会话
        school_slug: 学校 slug（如 tsinghua）
        year: 报告年份
        direct_url: 直接提供报告 URL（跳过入口页搜索）

    Returns:
        ReportRecord 或 None（学校不存在时）
    """
    school = db.query(School).filter(School.slug == school_slug).first()
    if not school:
        return None

    # 确定报告 URL
    if direct_url:
        report_url = direct_url
    elif school.report_index_url:
        report_url = _find_report_url(school.report_index_url, year)
        if not report_url:
            # 入口页未匹配到报告链接，回退直接抓取入口页本身
            report_url = school.report_index_url
    else:
        report = ReportRecord(
            school_id=school.id,
            year=year,
            source_url="",
            parse_status=ParseStatus.failed,
            parse_error="学校未配置 report_index_url",
        )
        db.add(report)
        db.commit()
        return report

    # 抓取报告内容
    html_content, status_code = _fetch_url(report_url)
    if html_content is None:
        if status_code is not None:
            error_msg = f"抓取失败: HTTP {status_code}"
        else:
            error_msg = "抓取失败: HTTP 错误或网络超时"
        report = ReportRecord(
            school_id=school.id,
            year=year,
            source_url=report_url,
            parse_status=ParseStatus.failed,
            parse_error=error_msg,
        )
        db.add(report)
        db.commit()
        return report

    report = ReportRecord(
        school_id=school.id,
        year=year,
        source_url=report_url,
        raw_html=html_content,
        parse_status=ParseStatus.pending,
    )
    db.add(report)
    db.commit()
    return report


def _find_report_url(index_url: str, year: int) -> str | None:
    """从入口页搜索指定年份的报告链接"""
    html, _ = _fetch_url(index_url)
    if not html:
        return None
    # 搜索包含年份关键词的链接
    pattern = rf'href=["\']([^"\']*{year}[^"\']*(?:就业|employment|report)[^"\']*)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        from urllib.parse import urljoin
        return urljoin(index_url, matches[0])
    return None


def _fetch_url(url: str) -> tuple[str | None, int | None]:
    """带重试的 HTTP GET。

    Returns:
        (content, status_code)：成功时 content 为响应文本、status_code 为 200；
        失败时 content 为 None，status_code 为 HTTP 状态码（网络异常时为 None）。
    """
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            resp = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text, 200
            if resp.status_code == 404:
                return None, 404
            # 其他非 200 状态码：继续重试
        except httpx.RequestError:
            pass
        if attempt < MAX_RETRIES - 1:
            time.sleep(REQUEST_DELAY * (attempt + 2))
    return None, None
