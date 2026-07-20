# backend/pipeline/fetcher.py
"""高校就业质量报告抓取器"""
import asyncio
import random
import re
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy.orm import Session

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus

USER_AGENT = "GradPathBot/1.0 (career research; +https://github.com/gradpath)"
REQUEST_DELAY = 1  # 秒，基础请求间隔（优化：从3减至1，加 jitter 防惊群）
TIMEOUT = 30
MAX_RETRIES = 3


def _jittered_delay(base: float = REQUEST_DELAY) -> float:
    """在基础延迟上添加 ±50% 随机抖动，防止多 worker 同时请求。"""
    return base * (0.5 + random.random())


def check_robots_allowed(url: str) -> bool:
    """检查 robots.txt 是否允许抓取"""
    try:
        rp = RobotFileParser()
        rp.set_url(url + "/robots.txt" if not url.endswith("/") else url + "robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        # fail-closed：无法读取 robots.txt 时默认禁止抓取，避免误抓取被禁止的内容
        return False


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

    # robots.txt 合规校验：发起 HTTP 请求前检查是否允许抓取
    if not check_robots_allowed(report_url):
        report = ReportRecord(
            school_id=school.id,
            year=year,
            source_url=report_url,
            parse_status=ParseStatus.failed,
            parse_error="robots.txt 禁止抓取该 URL",
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
    """带重试的 HTTP GET（同步版本）。

    优化：首次请求不延迟，仅重试时加 jittered 退避，避免不必要的等待。
    Returns:
        (content, status_code)：成功时 content 为响应文本、status_code 为 200；
        失败时 content 为 None，status_code 为 HTTP 状态码（网络异常时为 None）。
    """
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                import time
                time.sleep(_jittered_delay(REQUEST_DELAY * (attempt + 1)))
            resp = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text, 200
            if resp.status_code == 404:
                return None, 404
        except httpx.RequestError:
            pass
    return None, None


async def _fetch_url_async(url: str, client: httpx.AsyncClient | None = None) -> tuple[str | None, int | None]:
    """带重试的异步 HTTP GET。

    在 async 上下文中使用，不会阻塞事件循环。
    """
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                await asyncio.sleep(_jittered_delay(REQUEST_DELAY * (attempt + 1)))
            if client:
                resp = await client.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            else:
                async with httpx.AsyncClient() as ac:
                    resp = await ac.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text, 200
            if resp.status_code == 404:
                return None, 404
        except httpx.RequestError:
            pass
    return None, None


async def _find_report_url_async(index_url: str, year: int, client: httpx.AsyncClient | None = None) -> str | None:
    """从入口页搜索指定年份的报告链接（异步版本）"""
    html, _ = await _fetch_url_async(index_url, client)
    if not html:
        return None
    pattern = rf'href=["\']([^"\']*{year}[^"\']*(?:就业|employment|report)[^"\']*)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        from urllib.parse import urljoin
        return urljoin(index_url, matches[0])
    return None


async def fetch_report_async(
    db: Session,
    school_slug: str,
    year: int,
    direct_url: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> ReportRecord | None:
    """抓取指定学校的指定年份就业质量报告（异步版本）。

    在 async 上下文中使用，不会阻塞事件循环。
    """
    school = db.query(School).filter(School.slug == school_slug).first()
    if not school:
        return None

    if direct_url:
        report_url = direct_url
    elif school.report_index_url:
        report_url = await _find_report_url_async(school.report_index_url, year, client)
        if not report_url:
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

    if not check_robots_allowed(report_url):
        report = ReportRecord(
            school_id=school.id,
            year=year,
            source_url=report_url,
            parse_status=ParseStatus.failed,
            parse_error="robots.txt 禁止抓取该 URL",
        )
        db.add(report)
        db.commit()
        return report

    html_content, status_code = await _fetch_url_async(report_url, client)
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
