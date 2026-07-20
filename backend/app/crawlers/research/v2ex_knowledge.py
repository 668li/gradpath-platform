# -*- coding: utf-8 -*-
"""V2EX 考研就业讨论爬取器 — 抓取 V2EX 社区职业/考研相关讨论并导入知识库。

目标节点：qna(问答), career(职场), job(求职), graduate(研究生)
每个节点爬取 50 条帖子，提取标题、内容、作者、回复数等信息。

Usage (inside Docker):
    docker exec gradpath-backend-1 python /app/app/crawlers/research/v2ex_knowledge.py

Or locally:
    cd backend
    python -m app.crawlers.research.v2ex_knowledge
"""
import sys
import uuid
import time
import json
import re
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Add backend to path if running locally
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select, func
from app.database import Base, SessionLocal, engine
from app.models.knowledge_article import KnowledgeArticle

# Configuration
NODES = ["qna", "career", "job", "graduate"]
TOPICS_PER_NODE = 50
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
V2EX_API_BASE = "https://www.v2ex.com/api/topics/show.json"
V2EX_TOPIC_URL = "https://www.v2ex.com/t/{topic_id}"
V2EX_NODE_URL = "https://www.v2ex.com/go/{node}"

# Rate limiting
REQUEST_DELAY = 2.0  # seconds between requests


class V2EXKnowledgeCrawler:
    """V2EX 社区讨论爬取器"""

    def __init__(self):
        self.stats = {
            "fetched": 0,
            "imported": 0,
            "duplicates": 0,
            "errors": 0,
        }
        self.client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    def fetch_topics_api(self, node: str, limit: int = 50) -> list[dict]:
        """通过 V2EX API 获取节点下的帖子"""
        topics = []
        try:
            # API 返回的是最近活跃的帖子，我们请求足够多然后取前 limit 条
            url = f"{V2EX_API_BASE}?node_name={node}"
            resp = self.client.get(url)

            if resp.status_code == 403:
                print(f"  ⚠ API 返回 403，切换到 HTML 解析模式")
                return []

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list):
                topics = data[:limit]
            elif isinstance(data, dict) and "topics" in data:
                topics = data["topics"][:limit]

            self.stats["fetched"] += len(topics)
            return topics

        except httpx.HTTPStatusError as e:
            print(f"  ⚠ API 请求失败: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"  ⚠ API 请求异常: {e}")
            return []

    def fetch_topics_html(self, node: str, limit: int = 50) -> list[dict]:
        """通过 HTML 页面解析获取帖子（API 不可用时的备选方案）"""
        topics = []
        try:
            # 获取节点页面
            url = V2EX_NODE_URL.format(node=node)
            resp = self.client.get(url)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 解析帖子列表
            topic_items = soup.select("div.cell.item")

            for item in topic_items[:limit]:
                try:
                    # 提取标题和链接
                    title_elem = item.select_one("span.item_title a")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    topic_id_match = re.search(r"/t/(\d+)", href)
                    if not topic_id_match:
                        continue

                    topic_id = int(topic_id_match.group(1))

                    # 提取作者
                    author_elem = item.select_one("span.small a")
                    author = author_elem.get_text(strip=True) if author_elem else "unknown"

                    # 提取回复数
                    replies_elem = item.select_one("a.count_livid")
                    replies_count = int(replies_elem.get_text(strip=True)) if replies_elem else 0

                    topics.append({
                        "id": topic_id,
                        "title": title,
                        "node": {"name": node},
                        "member": {"username": author},
                        "replies": replies_count,
                        "created": int(time.time()),  # 近似时间
                        "url": f"https://www.v2ex.com{href}",
                    })

                    self.stats["fetched"] += 1

                except Exception as e:
                    print(f"  ⚠ 解析单个帖子失败: {e}")
                    continue

            return topics

        except Exception as e:
            print(f"  ⚠ HTML 解析失败: {e}")
            return []

    def fetch_topic_content(self, topic_id: int) -> str:
        """获取单个帖子的详细内容"""
        try:
            url = V2EX_TOPIC_URL.format(topic_id=topic_id)
            resp = self.client.get(url)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 提取主帖内容
            content_elem = soup.select_one("div.topic_content")
            if content_elem:
                # 移除 script 和 style 标签
                for tag in content_elem.find_all(["script", "style"]):
                    tag.decompose()
                return content_elem.get_text(separator="\n", strip=True)

            return ""

        except Exception as e:
            print(f"  ⚠ 获取帖子内容失败 (topic_id={topic_id}): {e}")
            return ""

    def parse_topic(self, topic: dict) -> dict:
        """解析帖子数据为标准格式"""
        topic_id = topic.get("id", 0)
        title = topic.get("title", "").strip()
        node_name = topic.get("node", {}).get("name", "unknown")
        author = topic.get("member", {}).get("username", "unknown")
        replies_count = topic.get("replies", 0)
        created_ts = topic.get("created", 0)

        # 解析创建时间
        try:
            created_at = datetime.fromtimestamp(created_ts, tz=timezone.utc)
        except (ValueError, TypeError):
            created_at = datetime.now(timezone.utc)

        # 获取帖子内容（API 可能不返回完整内容）
        content = topic.get("content", "") or ""
        if not content and topic_id:
            content = self.fetch_topic_content(topic_id)
            time.sleep(REQUEST_DELAY)

        # 清理内容
        content = self._clean_content(content) or title

        return {
            "topic_id": topic_id,
            "title": title,
            "content": content,
            "author": author,
            "node": node_name,
            "replies_count": replies_count,
            "created_at": created_at,
            "url": V2EX_TOPIC_URL.format(topic_id=topic_id),
        }

    def _clean_content(self, raw: str) -> str:
        """清理内容文本"""
        if not raw:
            return ""
        text = re.sub(r'\n{3,}', '\n\n', raw)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # 移除 Markdown 链接
        return text.strip()

    def store(self, items: list[dict], db) -> int:
        """存储数据到数据库"""
        if not items:
            return 0

        # 获取已存在的 topic_ids 用于去重
        existing_ids = self._get_existing_topic_ids(db, items)
        new_count = 0

        for item in items:
            topic_id = item["topic_id"]

            # 去重检查
            if topic_id in existing_ids:
                self.stats["duplicates"] += 1
                continue

            # 构建标签
            tags = [item["node"], "v2ex", "社区讨论"]

            # 构建 metadata
            metadata = {
                "source_type": "discussion",
                "v2ex_topic_id": topic_id,
                "author": item["author"],
                "replies_count": item["replies_count"],
                "node": item["node"],
                "url": item["url"],
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }

            # 创建 KnowledgeArticle
            article = KnowledgeArticle(
                id=uuid.uuid4(),
                category="career_experience",
                title=f"[V2EX·{item['node']}] {item['title'][:180]}",
                content=item["content"],
                tags=tags,
                source="v2ex",
                metadata_=metadata,
                is_published=True,
            )
            db.add(article)
            existing_ids.add(topic_id)
            new_count += 1

        db.commit()
        self.stats["imported"] += new_count
        return new_count

    def _get_existing_topic_ids(self, db, items: list[dict]) -> set:
        """获取已存在的 V2EX topic IDs"""
        topic_ids = [item["topic_id"] for item in items]
        if not topic_ids:
            return set()

        # 查询 metadata 中包含这些 topic_id 的记录
        existing = set()
        for topic_id in topic_ids:
            # 使用 JSONB 查询检查 metadata->>'v2ex_topic_id'
            stmt = select(KnowledgeArticle.id).where(
                KnowledgeArticle.source == "v2ex",
                KnowledgeArticle.metadata_["v2ex_topic_id"].astext == str(topic_id)
            )
            result = db.execute(stmt).first()
            if result:
                existing.add(topic_id)

        return existing

    def run(self):
        """执行完整的爬取流程"""
        print("=" * 60)
        print("V2EX 考研就业讨论爬取器")
        print("=" * 60)

        # 确保数据库表存在
        print("\n1. 检查数据库表...")
        Base.metadata.create_all(bind=engine)
        print("  ✓ 数据库表准备完成")

        db = SessionLocal()
        try:
            all_topics = []

            # 爬取每个节点
            print("\n2. 爬取 V2EX 节点...")
            for node in NODES:
                print(f"\n  节点: {node}")

                # 尝试 API
                topics = self.fetch_topics_api(node, TOPICS_PER_NODE)

                # API 失败则用 HTML 解析
                if not topics:
                    print(f"  → 使用 HTML 解析模式")
                    topics = self.fetch_topics_html(node, TOPICS_PER_NODE)

                print(f"  ✓ 获取 {len(topics)} 条帖子")
                all_topics.extend(topics)

                # 限速
                time.sleep(REQUEST_DELAY)

            # 解析帖子
            print(f"\n3. 解析 {len(all_topics)} 条帖子...")
            parsed_items = []
            for topic in all_topics:
                try:
                    parsed = self.parse_topic(topic)
                    parsed_items.append(parsed)
                except Exception as e:
                    print(f"  ⚠ 解析失败: {e}")
                    self.stats["errors"] += 1

            print(f"  ✓ 成功解析 {len(parsed_items)} 条")

            # 存储到数据库
            print("\n4. 导入数据库...")
            imported = self.store(parsed_items, db)
            print(f"  ✓ 新增导入 {imported} 条")

            # 统计信息
            total_ka = db.execute(select(func.count(KnowledgeArticle.id))).scalar()

            print("\n" + "=" * 60)
            print("爬取完成！统计信息：")
            print(f"  爬取节点: {', '.join(NODES)}")
            print(f"  获取帖子数: {self.stats['fetched']}")
            print(f"  成功解析数: {len(parsed_items)}")
            print(f"  新增导入数: {self.stats['imported']}")
            print(f"  重复跳过数: {self.stats['duplicates']}")
            print(f"  错误数: {self.stats['errors']}")
            print(f"  knowledge_articles 总数: {total_ka}")
            print("=" * 60)

            return self.stats

        except Exception as e:
            print(f"\n✗ 爬取失败: {e}")
            db.rollback()
            import traceback
            traceback.print_exc()
            self.stats["errors"] += 1
            return self.stats
        finally:
            db.close()
            self.client.close()


def main():
    """主函数"""
    crawler = V2EXKnowledgeCrawler()
    result = crawler.run()

    # 返回退出码
    if result["errors"] > 0 and result["imported"] == 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
