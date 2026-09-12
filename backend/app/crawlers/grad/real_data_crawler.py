"""真实数据爬虫 — 从高校官网、学位网抓取真实考研数据（spec 002 收敛版）。

数据源（全部 edu.cn 域，公开页）：
1. 各高校研究生院/研招办官网 — 招生信息页探测
2. 中国学位与研究生教育信息网 (cdgdc.edu.cn) — 学科评级

2026-09-12 地基收敛（spec 002）：
- **研招网分支整体根除**——yz.chsi.com.cn 是红线域（宪法+对抗审计 F2），
  本爬虫历史上抓它、产物被入库闸拒收，纯属浪费配额的红线试探；传输层
  现已直接拒绝该域外发。
- **预置缓存补位根除**——旧版"真实抓取失败回退预置缓存"违反零造假红线
  （R6 宁缺毋假）：抓不到就如实空手而归并记账，绝不拿编造的 quota/学费
  数字补位。_SCHOOL_CACHE 降级为纯抓取目标清单（配置，非数据）。
- 网络往返统一走 BaseCrawler._request（transport 统一传输层，带证据采集）。
"""

import json
import logging
import random

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# User-Agent 轮换池（仅请求头轮换，与数据真假无关）
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 真实数据源 URL 映射（红线域 yz.chsi.com.cn 不得出现在这里）
_REAL_DATA_SOURCES = {
    "学位网": {
        "base_url": "https://www.cdgdc.edu.cn",
        "rank_url": "https://www.cdgdc.edu.cn/xwyyjsjyxx/xkpg/",
    },
}

# 抓取目标清单（配置语义：要抓谁；不是数据，不入库）
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


def _get_random_headers() -> dict[str, str]:
    """返回随机 User-Agent 的请求头。"""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def _parse_cdgdc_rank(html: str) -> list[dict]:
    """解析学位网学科评级页面。"""
    results = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                results.append(
                    {
                        "discipline": cols[0].get_text(strip=True),
                        "university": cols[1].get_text(strip=True),
                        "rating": cols[2].get_text(strip=True),
                    }
                )
    except Exception as e:
        logger.error(f"Failed to parse CDGDC rankings: {e}")
    return results


# 审核条目的来源回退站点（仅有缓存/无真实 URL 时用于构造稳定的幂等 URL）
_SOURCE_BASE_URL = {
    "学位网": "https://www.cdgdc.edu.cn/xwyyjsjyxx/xkpg/",
}


def _review_url(item: dict) -> str:
    """生成审核条目的 source_url。

    优先使用真实来源 URL（高校官网）；无 website 的条目用"来源站点 + 锚点"
    构造稳定幂等的 URL，锚点携带来源与条目标识，保证重复抓取不产生重复条目。
    """
    website = (item.get("website") or "").strip()
    if website:
        return website[:500]
    source = (item.get("data_sources") or ["unknown"])[0]
    base = _SOURCE_BASE_URL.get(source, "https://www.cdgdc.edu.cn")
    school = item.get("school_name", "")
    key = item.get("major_name") or item.get("discipline") or school
    return f"{base}#real_data:{source}:{school}:{key}"


def _to_queue_item(item: dict) -> dict:
    """把 real_data 解析产物映射为审核队列条目（ExternalResearchItem 核心列）。

    仅提供 title / content / source_url 三个核心字段，
    data_sources / tags 等其余字段由 store_research_items 自动写入 external_meta，
    保留行级来源元数据（数据真实性红线：外部数据须来源标注）。
    """
    school = item.get("school_name", "")
    if item.get("discipline"):
        title = f"学科评级：{school} {item.get('discipline', '')}"
    else:
        title = f"院校信息：{school}"
    return {
        "title": title[:300],
        "content": json.dumps(item, ensure_ascii=False),
        "source_url": _review_url(item),
        # 地基⑤：透传 run() 统一盖的抓取证据章——fetched 态入库闸要求三齐全
        "fetch_evidence": item.get("fetch_evidence"),
    }


@register_crawler
class RealDataCrawler(BaseCrawler):
    """真实数据爬虫 — 从高校官网、学位网抓取真实考研数据。

    宁缺毋假（R6）：真实抓取失败时如实空手而归并记账，不回退任何预置数据。
    """

    name = "real_data"
    category = "grad"
    description = "真实数据爬虫（高校官网、学位网；研招网红线域已根除）"

    def fetch(self) -> list[dict]:
        """从多个数据源抓取真实数据；失败=空手而归，绝不补位。"""
        all_data = []

        # 数据源1: 高校官网
        school_data = self._fetch_school_data()
        if school_data:
            all_data.extend(school_data)

        # 数据源2: 学位网
        discipline_data = self._fetch_discipline_data()
        if discipline_data:
            all_data.extend(discipline_data)

        return all_data

    def _fetch_school_data(self) -> list[dict]:
        """从各高校研究生院官网抓取数据（探测可达性，写审核队列）。"""
        results = []
        schools_to_fetch = list(_SCHOOL_CACHE.keys())[:5]  # 限制前5所

        for school_name in schools_to_fetch:
            school_info = _SCHOOL_CACHE.get(school_name, {})
            website = school_info.get("website", "")
            if not website:
                continue
            try:
                resp = self._request(website, headers=_get_random_headers())
                if resp.status_code == 200:
                    results.append(
                        {
                            "source": "高校官网",
                            "type": "school",
                            "data": {
                                "name": school_name,
                                "website": website,
                                "html_length": len(resp.text),
                                "status": "fetched",
                            },
                        }
                    )
                    logger.info(f"Fetched data from {school_name} website")
            except Exception as e:
                logger.warning(f"Fetch failed for {school_name} ({website}): {e}")

        return results

    def _fetch_discipline_data(self) -> list[dict]:
        """从学位网抓取学科评级数据。"""
        results = []
        try:
            url = _REAL_DATA_SOURCES["学位网"]["rank_url"]
            resp = self._request(url, headers=_get_random_headers())
            if resp.status_code == 200:
                parsed = _parse_cdgdc_rank(resp.text)
                for item in parsed:
                    results.append(
                        {
                            "source": "学位网",
                            "type": "discipline",
                            "data": item,
                        }
                    )
                logger.info(f"Fetched {len(results)} discipline ratings from 学位网")
            else:
                logger.warning("Failed to fetch from 学位网")
        except Exception as e:
            logger.error(f"Error fetching from 学位网: {e}")
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

    def _parse_discipline_data(self, data: dict, source: str) -> dict:
        """解析学科评级数据。"""
        return {
            "discipline": data.get("discipline", ""),
            "school_name": data.get("university", ""),
            "rating": data.get("rating", ""),
            "data_sources": [source],
            "tags": ["学科评级"],
        }

    def store(self, items: list[dict], db: Session = None) -> int:
        """将解析后的数据写入审核队列（PENDING），不直接进业务表。

        合规红线（仅人工确认入库）：高校官网/学位网等外部数据一律先写
        t_external_research_item + t_review_queue_item（review_status=PENDING），
        由管理员在 admin 端人工确认后才落业务表（research_promote 消费）。
        本方法不调用 batch_upsert / 不写任何业务表。
        """
        from app.models.crawler_run import CrawlerRun
        from app.services.research_ingestion import store_research_items

        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        try:
            run_record = CrawlerRun(
                source_name=self.name,
                category=self.category,
                status="running",
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

            queue_items = [_to_queue_item(item) for item in items if item.get("school_name")]
            result = store_research_items(
                db,
                crawler_name=self.name,
                item_type="kaoyan_news",
                items=queue_items,
                source_platform="web",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "note": "高校官网/学位网数据：仅人工确认后入库（PENDING 审核队列）",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]
            logger.info(
                f"[{self.name}] 写入审核队列 {result['inserted']} 条，去重 {result['duplicated']} 条"
            )
            return result["inserted"]
        except Exception as e:
            db.rollback()
            logger.error(f"[{self.name}] 写入审核队列失败: {e}")
            self.stats["errors"] += 1
            raise
        finally:
            if own_db:
                db.close()
