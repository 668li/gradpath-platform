"""将外部调研 crawler 输出注入数据库。

读取 B站视频、网页文章、RSS 资讯三个 crawler 的 JSON 输出，经 ResearchTransformer
清洗去重后写入 ExperiencePost / KaoyanNews 表。

使用方式（项目根目录执行）：
    python backend/app/seed/seed_from_research.py
    python backend/app/seed/seed_from_research.py --approve
"""
import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path
from uuid import UUID

# 脚本从项目根目录运行时，把 backend 加入 sys.path
if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[2]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from app.crawlers.research.transformer import (
    SYSTEM_USER_ID,
    ResearchTransformer,
)
from app.database import Base, SessionLocal, engine
from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews
from app.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_WEB_ARTICLE_PATH = Path(tempfile.gettempdir()) / "web_article_research.json"
DEFAULT_RSS_NEWS_PATH = Path(tempfile.gettempdir()) / "rss_news_research.json"


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning(f"文件不存在，跳过: {path}")
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logger.warning(f"文件内容不是列表: {path}")
        return []
    except Exception as e:
        logger.error(f"读取文件失败 {path}: {e}")
        return []


def _load_bilibili_items() -> list[dict]:
    tmp_dir = Path(tempfile.gettempdir())
    paths = list(tmp_dir.glob("bilibili_research_*.json"))
    items: list[dict] = []
    for path in paths:
        items.extend(_load_json(path))
    logger.info(f"B站调研数据：从 {len(paths)} 个文件读取 {len(items)} 条原始记录")
    return items


def _ensure_system_user(db: Session) -> User:
    user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
    if not user:
        user = User(
            id=SYSTEM_USER_ID,
            email="system@gradpath.local",
            name="系统",
            password_hash="",
        )
        db.add(user)
        db.commit()
        logger.info("创建系统用户")
    return user


def _experience_post_exists(db: Session, source_url: str) -> bool:
    if not source_url:
        return False
    return (
        db.query(ExperiencePost.id)
        .filter(ExperiencePost.source_url == source_url)
        .first()
        is not None
    )


def _kaoyan_news_exists(db: Session, source_url: str) -> bool:
    if not source_url:
        return False
    return (
        db.query(KaoyanNews.id)
        .filter(KaoyanNews.source_url == source_url)
        .first()
        is not None
    )


def _import_experience_posts(db: Session, payloads: list[dict], approve: bool = False) -> int:
    """将清洗后的经验贴 payload 写入 ExperiencePost，返回新增条数。"""
    target_status = "approved" if approve else "pending"
    count = 0
    for payload in payloads:
        source_url = payload.get("source_url", "")
        if _experience_post_exists(db, source_url):
            continue
        payload["status"] = target_status
        post = ExperiencePost(**payload)
        db.add(post)
        count += 1
    if count:
        db.commit()
    return count


def _import_kaoyan_news(db: Session, payloads: list[dict], approve: bool = False) -> int:
    """将清洗后的资讯 payload 写入 KaoyanNews，返回新增条数。"""
    target_status = "approved" if approve else "pending"
    count = 0
    for payload in payloads:
        source_url = payload.get("source_url", "")
        if _kaoyan_news_exists(db, source_url):
            continue
        payload["status"] = target_status
        news = KaoyanNews(**payload)
        db.add(news)
        count += 1
    if count:
        db.commit()
    return count


def import_bilibili_research(db: Session, items: list[dict], approve: bool = False) -> int:
    """将 B站 crawler 输出导入数据库，返回新增经验贴条数。"""
    _ensure_system_user(db)
    payloads = ResearchTransformer.transform_bilibili(items)
    return _import_experience_posts(db, payloads, approve=approve)


def import_web_research(db: Session, items: list[dict], approve: bool = False) -> int:
    """将网页文章 crawler 输出导入数据库，返回新增经验贴条数。"""
    _ensure_system_user(db)
    payloads = ResearchTransformer.transform_web(items)
    return _import_experience_posts(db, payloads, approve=approve)


def import_rss_research(db: Session, items: list[dict], approve: bool = False) -> int:
    """将 RSS crawler 输出导入数据库，返回新增资讯条数。"""
    _ensure_system_user(db)
    payloads = ResearchTransformer.transform_rss(items)
    return _import_kaoyan_news(db, payloads, approve=approve)


def seed_from_research(db: Session, approve: bool = False) -> dict[str, int]:
    """读取 crawler 输出并注入数据库。返回新增数量统计。"""
    # 确保模型对应的表已存在（开发模式；生产环境应通过 Alembic 迁移）
    Base.metadata.create_all(bind=engine)
    _ensure_system_user(db)

    bilibili_items = _load_bilibili_items()
    web_items = _load_json(DEFAULT_WEB_ARTICLE_PATH)
    rss_items = _load_json(DEFAULT_RSS_NEWS_PATH)

    transformed_bilibili = ResearchTransformer.transform_bilibili(bilibili_items)
    transformed_web = ResearchTransformer.transform_web(web_items)
    transformed_rss = ResearchTransformer.transform_rss(rss_items)

    stats = {
        "experience_posts": _import_experience_posts(
            db, transformed_bilibili + transformed_web, approve=approve
        ),
        "kaoyan_news": _import_kaoyan_news(db, transformed_rss, approve=approve),
    }

    return stats


def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(description="将调研数据注入数据库")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="直接审核通过（默认 pending）",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = seed_from_research(db, approve=args.approve)
        logger.info(
            "注入完成：新增 %d 条经验贴（B站+网页），%d 条考研资讯（RSS）",
            stats["experience_posts"],
            stats["kaoyan_news"],
        )
        print(
            f"注入完成：新增 {stats['experience_posts']} 条经验贴，"
            f"{stats['kaoyan_news']} 条考研资讯"
        )
    except Exception as e:
        logger.exception("注入失败: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
