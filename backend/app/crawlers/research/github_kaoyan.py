"""GitHub 考研/考公/求职资料仓库爬虫。

通过 GitHub Search API 搜索相关开源仓库，提取仓库元数据并导入
knowledge_articles 表，供 RAG 检索使用。
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from sqlalchemy.orm import Session

# 当以脚本直接运行时，确保 backend 目录在 sys.path 中以便 import app
if __name__ == "__main__":
    backend_dir = Path(__name__).resolve().parents[3] if __name__ == "__main__" else Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.database import SessionLocal
from app.models.knowledge_article import KnowledgeArticle

logger = logging.getLogger(__name__)

# 默认搜索关键词
DEFAULT_KEYWORDS = [
    "考研",
    "kaoyan",
    "考研资料",
    "考研真题",
    "考研经验",
    "考公",
    "civil-service-exam",
    "求职面试",
]


@register_crawler
class GitHubKaoyanCrawler(BaseCrawler):
    """通过 GitHub Search API 搜索考研/考公/求职相关仓库。"""

    name = "github_kaoyan"
    category = "research"
    description = "GitHub 考研/考公/求职资料仓库爬虫"

    GITHUB_SEARCH_API = "https://api.github.com/search/repositories"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.keywords = self.config.get("keywords", DEFAULT_KEYWORDS)
        self.per_page = int(self.config.get("per_page", 30))
        self.token = self.config.get("github_token")  # 可选 GitHub Token
        # GitHub API 限速：无 token 60次/小时，有 token 5000次/小时
        self._rate_limit = 2.0  # 请求间隔 2 秒，保守避免触发限速
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.session.headers["User-Agent"] = "GradPath-KaoyanCrawler/1.0"

    def fetch(self) -> list[dict]:
        """逐关键词调用 GitHub Search API，汇总所有仓库结果。"""
        all_items: list[dict] = []
        for kw in self.keywords:
            url = (
                f"{self.GITHUB_SEARCH_API}"
                f"?q={quote(kw)}"
                f"&sort=stars"
                f"&per_page={self.per_page}"
            )
            try:
                resp = self._request(url)
                data = resp.json()
                items = data.get("items", [])
                logger.info(
                    f"[{self.name}] 关键词「{kw}」返回 {len(items)} 条"
                )
                all_items.extend(items)
            except requests.HTTPError as e:
                # 处理 GitHub API 限速
                if e.response is not None and e.response.status_code == 403:
                    logger.warning(
                        f"[{self.name}] 触发 GitHub API 限速，跳过关键词「{kw}」"
                    )
                    self.stats["errors"] += 1
                else:
                    logger.error(f"[{self.name}] 请求失败: {e}")
                    self.stats["errors"] += 1
            except Exception as e:
                logger.error(f"[{self.name}] 关键词「{kw}」请求异常: {e}")
                self.stats["errors"] += 1
        return all_items

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将 GitHub API 返回的仓库数据转为 knowledge_articles 结构。"""
        parsed: list[dict] = []
        for item in raw_items:
            name = item.get("full_name") or item.get("name", "")
            description = item.get("description") or ""
            html_url = item.get("html_url", "")
            stars = item.get("stargazers_count", 0)
            language = item.get("language") or ""
            topics = item.get("topics") or []
            created_at = item.get("created_at", "")
            owner = (item.get("owner") or {}).get("login", "")

            # 拼接 content：description + topics + 元信息
            content_parts = []
            if description:
                content_parts.append(description)
            if topics:
                content_parts.append(f"**Topics:** {', '.join(topics)}")
            content_parts.append(f"**Stars:** {stars} | **Language:** {language} | **Owner:** {owner}")
            if created_at:
                content_parts.append(f"**Created:** {created_at[:10]}")
            content = "\n\n".join(content_parts)

            parsed.append({
                "category": "education_path",
                "title": f"[GitHub] {name}",
                "content": content,
                "tags": topics if topics else [language] if language else [],
                "source": "github",
                "metadata": {
                    "source_type": "repo",
                    "html_url": html_url,
                    "stargazers_count": stars,
                    "language": language,
                    "owner": owner,
                    "created_at": created_at,
                    "topics": topics,
                },
                "is_published": True,
            })
        return parsed

    def store(self, items: list[dict], db: Session) -> int:
        """按 html_url 去重后批量插入 knowledge_articles 表。"""
        if not items:
            return 0

        # 提取所有 html_url 用于去重
        urls = [item["metadata"]["html_url"] for item in items]
        existing = self.get_existing_keys(
            db, KnowledgeArticle, "source", []
        )
        # 通过 metadata JSONB 查询已有 URL（简单方案：逐条检查）
        existing_urls: set[str] = set()
        try:
            from sqlalchemy import text
            result = db.execute(
                text(
                    "SELECT metadata->>'html_url' FROM knowledge_articles "
                    "WHERE source = 'github' AND metadata->>'html_url' IS NOT NULL"
                )
            )
            existing_urls = {row[0] for row in result}
        except Exception as e:
            logger.warning(f"[{self.name}] 去重查询失败，将全量插入: {e}")

        # 过滤已存在的
        new_items = [
            item for item in items
            if item["metadata"]["html_url"] not in existing_urls
        ]
        skipped = len(items) - len(new_items)
        if skipped > 0:
            logger.info(f"[{self.name}] 去重跳过 {skipped} 条已存在记录")
            self.stats["duplicates"] = skipped

        if not new_items:
            return 0

        # 批量插入
        count = 0
        for item in new_items:
            try:
                article = KnowledgeArticle(
                    category=item["category"],
                    title=item["title"],
                    content=item["content"],
                    tags=item["tags"],
                    source=item["source"],
                    metadata=item["metadata"],
                    is_published=item["is_published"],
                )
                db.add(article)
                count += 1
            except Exception as e:
                logger.error(f"[{self.name}] 插入失败: {e}")
                self.stats["errors"] += 1

        db.commit()
        return count


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def main():
    parser = argparse.ArgumentParser(description="GitHub 考研/考公/求职资料仓库爬虫")
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=None,
        help="搜索关键词列表（默认使用内置关键词）",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=30,
        help="每个关键词返回的最大仓库数（默认30）",
    )
    parser.add_argument(
        "--github-token",
        default=None,
        help="GitHub Personal Access Token（可选，提高 API 限速）",
    )
    args = parser.parse_args()

    _setup_logging()

    config = {
        "per_page": args.per_page,
    }
    if args.keywords:
        config["keywords"] = args.keywords
    if args.github_token:
        config["github_token"] = args.github_token

    crawler = GitHubKaoyanCrawler(config=config)

    # 使用容器内 DB
    db = SessionLocal()
    try:
        result = crawler.run(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
