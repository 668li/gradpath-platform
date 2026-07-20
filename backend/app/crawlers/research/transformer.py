"""调研数据清洗、去重、结构化转换器。

将 B站视频、网页文章、RSS 资讯等原始 crawler 输出转换为可写入数据库的 payload。
"""
import html
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

# 系统用户 ID，用于发布种子/系统内容
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 广告/引流关键词（命中即丢弃）
AD_KEYWORDS = [
    "加微信",
    "领资料",
    "私信",
    "进群",
    "二维码",
    "优惠",
    "限时",
]

# 学科关键词
SUBJECT_KEYWORDS = [
    "408",
    "数据结构",
    "计算机组成原理",
    "操作系统",
    "计算机网络",
    "数学",
    "英语",
    "政治",
    "计算机",
    "金融",
    "法学",
    "教育学",
    "医学",
]

# 阶段关键词
STAGE_KEYWORDS = [
    "择校",
    "选校",
    "备考",
    "复习",
    "初试",
    "复试",
    "调剂",
    "上岸",
    "二战",
]

# 分类映射：按标题关键词归类
CATEGORY_RULES = [
    ("复试", ["复试"]),
    ("调剂", ["调剂"]),
    ("择校", ["择校", "选校"]),
    ("备考", ["备考", "初试"]),
    ("复习", ["复习"]),
]

# 用于判断 RSS 非中文条目是否与考研相关
KAOYAN_MARKERS = [
    "考研",
    "硕士",
    "研究生",
    "graduate",
    "master",
    "phd",
    "kaoyan",
]


class ResearchTransformer:
    """将外部调研 crawler 输出清洗、去重并结构化。"""

    @staticmethod
    def _strip_html(value: Any) -> str:
        """去除 HTML 标签并解码 HTML 实体。"""
        text = str(value) if value is not None else ""
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        return text

    @staticmethod
    def _clean_text(value: Any) -> str:
        """清理文本：去除首尾空白、统一换行。"""
        text = str(value) if value is not None else ""
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        return text

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _extract_tags(cls, text: str) -> list[str]:
        """从文本中提取学科与阶段标签。"""
        text = text.lower()
        tags: list[str] = []
        for kw in SUBJECT_KEYWORDS + STAGE_KEYWORDS:
            if kw.lower() in text and kw not in tags:
                tags.append(kw)
        return tags

    @classmethod
    def _infer_category(cls, title: str) -> str:
        """根据标题关键词推断经验贴分类。"""
        title_lower = title.lower()
        for category, keywords in CATEGORY_RULES:
            if any(kw.lower() in title_lower for kw in keywords):
                return category
        return "general"

    @classmethod
    def _contains_ad(cls, text: str) -> bool:
        """判断是否包含广告/引流关键词。"""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in AD_KEYWORDS)

    @classmethod
    def _is_kaoyan_related(cls, title: str) -> bool:
        """判断标题是否与考研相关（用于过滤 RSS 纯英文无关条目）。"""
        if any(kw.lower() in title.lower() for kw in KAOYAN_MARKERS):
            return True
        # 包含中文字符则认为与中文语境相关
        if re.search(r"[\u4e00-\u9fff]", title):
            return True
        return False

    @classmethod
    def _is_quality_ok(cls, title: str, content: str, platform: str) -> bool:
        """质量过滤：标题过短、含广告、纯英文且与考研无关的均丢弃。"""
        if len(title.strip()) < 5:
            return False
        if cls._contains_ad(title + "\n" + content):
            return False
        if platform == "rss" and not cls._is_kaoyan_related(title):
            return False
        return True

    @classmethod
    def _dedup_by_url(cls, items: list[dict]) -> list[dict]:
        """基于 source_url 去重，保留第一条。无 source_url 的条目会被丢弃。"""
        seen: set[str] = set()
        result: list[dict] = []
        for item in items:
            url = item.get("source_url")
            if not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            result.append(item)
        return result

    @classmethod
    def transform_bilibili(cls, items: list[dict]) -> list[dict]:
        """将 B站视频转换为 ExperiencePost payload。"""
        payloads: list[dict] = []
        for raw in items:
            title = cls._clean_text(cls._strip_html(raw.get("title", "")))
            author = cls._clean_text(raw.get("author", ""))
            bvid = cls._clean_text(raw.get("bvid", ""))
            source_url = cls._clean_text(raw.get("source_url", ""))
            if not source_url and bvid:
                source_url = f"https://www.bilibili.com/video/{bvid}"

            view_count = cls._to_int(raw.get("view_count"))
            like_count = cls._to_int(raw.get("like_count"))

            raw_summary = cls._clean_text(raw.get("summary") or raw.get("content") or title)
            raw_content = cls._clean_text(raw.get("content") or raw.get("summary") or title)

            if not cls._is_quality_ok(title, raw_content, "bilibili"):
                continue

            summary = raw_summary[:500]
            existing_tags = [t for t in raw.get("tags", []) if isinstance(t, str)]
            extracted_tags = cls._extract_tags(f"{title} {raw_content}")
            tags = list(dict.fromkeys(existing_tags + extracted_tags))
            category = cls._infer_category(title)

            content_lines = [
                f"作者：{author or '未知'}",
                f"播放量：{view_count}",
                f"标签：{', '.join(tags)}",
                "",
                raw_content,
            ]
            content = "\n".join(content_lines)

            payloads.append(
                {
                    "user_id": SYSTEM_USER_ID,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "tags": tags,
                    "category": category,
                    "source_platform": "bilibili",
                    "source_url": source_url,
                    "external_view_count": view_count,
                    "external_like_count": like_count,
                    "status": "pending",
                    "is_verified": False,
                    "is_anonymous": False,
                }
            )

        return cls._dedup_by_url(payloads)

    @classmethod
    def transform_web(cls, items: list[dict]) -> list[dict]:
        """将网页文章转换为 ExperiencePost payload。"""
        payloads: list[dict] = []
        for raw in items:
            raw_title = cls._clean_text(raw.get("title", ""))
            # Jina Reader 可能带有 "Title: " 前缀
            if raw_title.lower().startswith("title:"):
                raw_title = raw_title[6:].strip()
            title = cls._clean_text(cls._strip_html(raw_title))
            content = cls._clean_text(raw.get("content", ""))
            source_url = cls._clean_text(raw.get("source_url", ""))

            # 过滤掉反爬/登录拦截页面
            if any(
                marker in content
                for marker in [
                    "安全验证",
                    "CAPTCHA",
                    "please make sure you are authorized",
                    "请您登录后查看",
                ]
            ):
                continue

            if not cls._is_quality_ok(title, content, "web"):
                continue

            summary = content[:500]
            tags = cls._extract_tags(f"{title} {content}")
            category = cls._infer_category(title)

            payloads.append(
                {
                    "user_id": SYSTEM_USER_ID,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "tags": tags,
                    "category": category,
                    "source_platform": "web",
                    "source_url": source_url,
                    "external_view_count": 0,
                    "external_like_count": 0,
                    "status": "pending",
                    "is_verified": False,
                    "is_anonymous": False,
                }
            )

        return cls._dedup_by_url(payloads)

    @classmethod
    def transform_rss(cls, items: list[dict]) -> list[dict]:
        """将 RSS 资讯转换为 KaoyanNews payload。"""
        payloads: list[dict] = []
        for raw in items:
            title = cls._clean_text(cls._strip_html(raw.get("title", "")))
            summary = cls._clean_text(raw.get("summary", ""))[:500]
            content = cls._clean_text(raw.get("content", ""))
            source_url = cls._clean_text(raw.get("source_url", ""))

            if not cls._is_quality_ok(title, content or summary, "rss"):
                continue

            existing_tags = [t for t in raw.get("tags", []) if isinstance(t, str)]
            extracted_tags = cls._extract_tags(f"{title} {summary} {content}")
            tags = list(dict.fromkeys(existing_tags + extracted_tags))

            category = raw.get("category", "general") or "general"
            if isinstance(category, str) and len(category) > 50:
                category = "general"

            published_at = raw.get("published_at")
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at)
                except ValueError:
                    published_at = None
            elif not isinstance(published_at, datetime):
                published_at = None

            crawled_at = raw.get("crawled_at")
            if isinstance(crawled_at, str):
                try:
                    crawled_at = datetime.fromisoformat(crawled_at)
                except ValueError:
                    crawled_at = None
            if not isinstance(crawled_at, datetime):
                crawled_at = datetime.now(timezone.utc)

            payloads.append(
                {
                    "title": title,
                    "summary": summary or None,
                    "content": content or None,
                    "source_platform": raw.get("source_platform", "rss") or "rss",
                    "source_url": source_url,
                    "published_at": published_at,
                    "crawled_at": crawled_at,
                    "status": "pending",
                    "category": category,
                    "tags": tags,
                }
            )

        return cls._dedup_by_url(payloads)
