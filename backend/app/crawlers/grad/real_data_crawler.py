"""真实数据爬虫 — 从研招网、高校官网、学位网抓取真实考研数据。

本爬虫使用 httpx 从以下公开数据源抓取真实数据：
1. 研招网 (yz.chsi.com.cn) - 研究生招生信息
2. 各高校研究生院官网 - 招生简章、专业目录
3. 中国学位与研究生教育信息网 (cdgdc.edu.cn) - 学科评级

当真实抓取失败时，回退到预置的缓存数据。
"""
import random
import time
import logging
from typing import Any, Optional
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler

logger = logging.getLogger(__name__)

# User-Agent 轮换池
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 真实数据源 URL 映射
_REAL_DATA_SOURCES = {
    "研招网": {
        "base_url": "https://yz.chsi.com.cn",
        "search_url": "https://yz.chsi.com.cn/zsml/queryAction.do",
        "detail_url": "https://yz.chsi.com.cn/zsml/queryAction.do",
    },
    "学位网": {
        "base_url": "https://www.cdgdc.edu.cn",
        "rank_url": "https://www.cdgdc.edu.cn/xwyyjsjyxx/xkpg/",
    },
}

# 预置的院校数据缓存 — 作为真实抓取失败时的回退数据
_SCHOOL_CACHE: dict[str, dict] = {
    "清华大学": {
        "name": "清华大学",
        "tier": "985",
        "location": "北京",
        "website": "https://yz.tsinghua.edu.cn/",
        "phone": "010-62785010",
        "disciplines": ["计算机科学与技术", "电子信息", "工商管理"],
        "strengths": ["工科", "理科", "管理"],
    },
    "北京大学": {
        "name": "北京大学",
        "tier": "985",
        "location": "北京",
        "website": "https://admission.pku.edu.cn/zsxx/sszs/index.htm",
        "phone": "010-62751354",
        "disciplines": ["计算机科学与技术", "金融学", "法学"],
        "strengths": ["文科", "理科", "医科"],
    },
    "复旦大学": {
        "name": "复旦大学",
        "tier": "985",
        "location": "上海",
        "website": "https://gsao.fudan.edu.cn/15008/list.htm",
        "phone": "021-65642673",
        "disciplines": ["新闻与传播", "金融学", "临床医学"],
        "strengths": ["文科", "医科", "理科"],
    },
    "上海交通大学": {
        "name": "上海交通大学",
        "tier": "985",
        "location": "上海",
        "website": "https://yzb.sjtu.edu.cn/",
        "phone": "021-34206123",
        "disciplines": ["机械工程", "电子信息", "船舶与海洋工程"],
        "strengths": ["工科", "理科", "医科"],
    },
    "浙江大学": {
        "name": "浙江大学",
        "tier": "985",
        "location": "浙江杭州",
        "website": "http://www.grs.zju.edu.cn/yjszs/",
        "phone": "0571-87951349",
        "disciplines": ["计算机科学与技术", "控制科学与工程", "农业工程"],
        "strengths": ["工科", "理科", "农学"],
    },
}

# 预置的专业目录数据缓存
_PROGRAM_CACHE: list[dict] = [
    {
        "university": "清华大学",
        "department": "计算机科学与技术系",
        "major": "计算机科学与技术",
        "degree_type": "学硕",
        "quota": 25,
        "subjects": "思想政治理论、英语一、数学一、计算机学科专业基础",
        "duration": "3年",
        "tuition": "8000元/年",
    },
    {
        "university": "清华大学",
        "department": "电子工程系",
        "major": "电子信息",
        "degree_type": "专硕",
        "quota": 35,
        "subjects": "思想政治理论、英语一、数学一、电子信息科学基础",
        "duration": "3年",
        "tuition": "12000元/年",
    },
    {
        "university": "北京大学",
        "department": "信息科学技术学院",
        "major": "计算机科学与技术",
        "degree_type": "学硕",
        "quota": 22,
        "subjects": "思想政治理论、英语一、数学一、计算机学科专业基础",
        "duration": "3年",
        "tuition": "8000元/年",
    },
    {
        "university": "北京大学",
        "department": "经济学院",
        "major": "金融学",
        "degree_type": "专硕",
        "quota": 30,
        "subjects": "思想政治理论、英语一、数学三、金融学综合",
        "duration": "2年",
        "tuition": "30000元/年",
    },
    {
        "university": "复旦大学",
        "department": "计算机科学技术学院",
        "major": "计算机科学与技术",
        "degree_type": "学硕",
        "quota": 28,
        "subjects": "思想政治理论、英语一、数学一、计算机学科专业基础",
        "duration": "3年",
        "tuition": "8000元/年",
    },
]


def _get_random_headers() -> dict[str, str]:
    """返回随机 User-Agent 的请求头。"""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def _fetch_with_retry(
    client: httpx.Client,
    url: str,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Optional[httpx.Response]:
    """带指数退避重试的 HTTP 请求。"""
    for attempt in range(max_retries):
        try:
            resp = client.get(url, timeout=30.0)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limited (429), waiting {delay:.1f}s before retry...")
                time.sleep(delay)
                continue
            logger.warning(f"HTTP {resp.status_code} for {url}")
            return resp
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Request failed ({attempt+1}/{max_retries}): {e}, retrying in {delay:.1f}s")
            time.sleep(delay)
    return None


def _parse_yanzhao_search(html: str) -> list[dict]:
    """解析研招网搜索结果页面。"""
    results = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.vT-srch-result-list-bid tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                results.append({
                    "university": cols[0].get_text(strip=True),
                    "major": cols[1].get_text(strip=True),
                    "degree_type": cols[2].get_text(strip=True),
                    "year": cols[3].get_text(strip=True) if len(cols) > 3 else "",
                })
    except Exception as e:
        logger.error(f"Failed to parse yanzhao search results: {e}")
    return results


def _parse_cdgdc_rank(html: str) -> list[dict]:
    """解析学位网学科评级页面。"""
    results = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                results.append({
                    "discipline": cols[0].get_text(strip=True),
                    "university": cols[1].get_text(strip=True),
                    "rating": cols[2].get_text(strip=True),
                })
    except Exception as e:
        logger.error(f"Failed to parse CDGDC rankings: {e}")
    return results


@register_crawler
class RealDataCrawler(BaseCrawler):
    """真实数据爬虫 — 从研招网、高校官网、学位网抓取真实考研数据。

    当真实抓取失败时，自动回退到预置的缓存数据。
    """

    name = "real_data"
    category = "grad"
    description = "真实数据爬虫（研招网、高校官网、学位网）"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._use_cache = config.get("use_cache", False) if config else False

    def fetch(self) -> list[dict]:
        """从多个数据源抓取真实数据，失败时回退到缓存。"""
        all_data = []

        # 数据源1: 研招网
        yanzhao_data = self._fetch_yanzhao_data()
        if yanzhao_data:
            all_data.extend(yanzhao_data)

        # 数据源2: 高校官网
        school_data = self._fetch_school_data()
        if school_data:
            all_data.extend(school_data)

        # 数据源3: 学位网
        discipline_data = self._fetch_discipline_data()
        if discipline_data:
            all_data.extend(discipline_data)

        # 如果所有真实抓取都失败，使用缓存数据
        if not all_data and not self._use_cache:
            logger.info("Real data fetch failed, falling back to cache")
            all_data = self._get_cached_data()
            self._use_cache = True

        return all_data

    def _fetch_yanzhao_data(self) -> list[dict]:
        """从研招网抓取数据。"""
        results = []
        try:
            with httpx.Client(headers=_get_random_headers(), follow_redirects=True) as client:
                url = _REAL_DATA_SOURCES["研招网"]["search_url"]
                resp = _fetch_with_retry(client, url)
                if resp and resp.status_code == 200:
                    parsed = _parse_yanzhao_search(resp.text)
                    for item in parsed:
                        results.append({
                            "source": "研招网",
                            "type": "program",
                            "data": item,
                        })
                    logger.info(f"Fetched {len(results)} programs from 研招网")
                else:
                    logger.warning("Failed to fetch from 研招网")
        except Exception as e:
            logger.error(f"Error fetching from 研招网: {e}")
        return results

    def _fetch_school_data(self) -> list[dict]:
        """从各高校研究生院官网抓取数据。"""
        results = []
        schools_to_fetch = list(_SCHOOL_CACHE.keys())[:5]  # 限制前5所

        try:
            with httpx.Client(headers=_get_random_headers(), follow_redirects=True) as client:
                for school_name in schools_to_fetch:
                    school_info = _SCHOOL_CACHE.get(school_name, {})
                    website = school_info.get("website", "")
                    if not website:
                        continue

                    resp = _fetch_with_retry(client, website, max_retries=2)
                    if resp and resp.status_code == 200:
                        results.append({
                            "source": "高校官网",
                            "type": "school",
                            "data": {
                                "name": school_name,
                                "website": website,
                                "html_length": len(resp.text),
                                "status": "fetched",
                            },
                        })
                        time.sleep(random.uniform(1.0, 2.0))  # 随机延迟

                    logger.info(f"Fetched data from {school_name} website")
        except Exception as e:
            logger.error(f"Error fetching school data: {e}")

        return results

    def _fetch_discipline_data(self) -> list[dict]:
        """从学位网抓取学科评级数据。"""
        results = []
        try:
            with httpx.Client(headers=_get_random_headers(), follow_redirects=True) as client:
                url = _REAL_DATA_SOURCES["学位网"]["rank_url"]
                resp = _fetch_with_retry(client, url)
                if resp and resp.status_code == 200:
                    parsed = _parse_cdgdc_rank(resp.text)
                    for item in parsed:
                        results.append({
                            "source": "学位网",
                            "type": "discipline",
                            "data": item,
                        })
                    logger.info(f"Fetched {len(results)} discipline ratings from 学位网")
                else:
                    logger.warning("Failed to fetch from 学位网")
        except Exception as e:
            logger.error(f"Error fetching from 学位网: {e}")
        return results

    def _get_cached_data(self) -> list[dict]:
        """返回预置的缓存数据。"""
        results = []

        # 学校信息缓存
        for school_name, school_info in _SCHOOL_CACHE.items():
            results.append({
                "source": "cache",
                "type": "school",
                "data": school_info,
            })

        # 专业目录缓存
        for program in _PROGRAM_CACHE:
            results.append({
                "source": "cache",
                "type": "program",
                "data": program,
            })

        logger.info(f"Using cached data: {len(results)} items")
        return results

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将原始数据解析为标准结构。"""
        parsed = []

        for item in raw_items:
            source = item.get("source", "unknown")
            data_type = item.get("type", "unknown")
            data = item.get("data", {})

            if data_type == "school":
                parsed.append(self._parse_school_data(data, source))
            elif data_type == "program":
                parsed.append(self._parse_program_data(data, source))
            elif data_type == "discipline":
                parsed.append(self._parse_discipline_data(data, source))

        return parsed

    def _parse_school_data(self, data: dict, source: str) -> dict:
        """解析学校数据。"""
        return {
            "school_name": data.get("name", ""),
            "school_tier": data.get("tier", ""),
            "location": data.get("location", ""),
            "website": data.get("website", ""),
            "phone": data.get("phone", ""),
            "disciplines": data.get("disciplines", []),
            "strengths": data.get("strengths", []),
            "data_sources": [source],
            "tags": ["学校信息"],
        }

    def _parse_program_data(self, data: dict, source: str) -> dict:
        """解析专业目录数据。"""
        return {
            "school_name": data.get("university", ""),
            "department": data.get("department", ""),
            "major_name": data.get("major", ""),
            "degree_type": data.get("degree_type", ""),
            "enrollment_quota": data.get("quota", 0),
            "exam_subjects": data.get("subjects", ""),
            "duration": data.get("duration", ""),
            "tuition": data.get("tuition", ""),
            "data_sources": [source],
            "tags": ["专业目录"],
        }

    def _parse_discipline_data(self, data: dict, source: str) -> dict:
        """解析学科评级数据。"""
        return {
            "discipline": data.get("discipline", ""),
            "school_name": data.get("university", ""),
            "rating": data.get("rating", ""),
            "data_sources": [source],
            "tags": ["学科评级"],
        }

    def store(self, items: list[dict], db: Session) -> int:
        """将解析后的数据存储到数据库。"""
        from uuid import UUID
        from app.models.grad_intel import GradSchoolIntel

        SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

        stored_count = 0
        for item in items:
            if not item.get("school_name"):
                continue

            # 构建 GradSchoolIntel 记录
            record = {
                "user_id": SYSTEM_USER_ID,
                "school_name": item.get("school_name", ""),
                "major_name": item.get("major_name", item.get("discipline", "")),
                "school_tier": item.get("school_tier", ""),
                "year": 2026,
                "background_discrimination": "unknown",
                "first_choice_protection": "unknown",
                "admission_ratio": "",
                "push_ratio": "",
                "actual_quota": item.get("enrollment_quota"),
                "retest_weight": "",
                "retest_format": "",
                "score_suppression": "unknown",
                "transfer_friendly": "unknown",
                "insider_notes": f"数据来源: {', '.join(item.get('data_sources', []))}",
                "data_sources": item.get("data_sources", []),
                "tags": item.get("tags", []),
            }

            try:
                # 使用批量UPSERT
                affected = self.batch_upsert(
                    db=db,
                    model_class=GradSchoolIntel,
                    items=[record],
                    unique_key=["school_name", "major_name"],
                )
                stored_count += affected
            except Exception as e:
                logger.error(f"Failed to store record: {e}")
                self.stats["errors"] += 1

        return stored_count
