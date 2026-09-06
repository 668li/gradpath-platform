"""将外部调研数据注入业务表（开发工具，非生产导入通道）。

数据来源：``app/crawlers/real_data/`` 下的真实抓取 JSON（B3 已统一适配），
经 ResearchTransformer 清洗去重后写入 ExperiencePost / KaoyanNews 表。

注意（B1/B3 合规收口后）：
- 生产导入通道是 ``scripts/import_real_data_to_queue.py``（真实数据 → PENDING 审核队列 →
  人工 confirm → research_promote 落业务表）。本脚本是直接注入的开发工具，
  默认写入 status=pending，供本地演示/验收使用，不要在生产环境自动调用。
- 原 tempfile 落盘路径已废弃（爬虫 B1 后直接走 store_research_items 入库），
  现统一从 real_data/ 读取，且复用 B3 脚本的适配器（单一数据来源）。

使用方式（backend 目录执行）：
    python app/seed/seed_from_research.py
    python app/seed/seed_from_research.py --approve
"""

import argparse
import logging
import sys
from pathlib import Path

# 脚本从项目根目录运行时，把 backend 加入 sys.path
if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[2]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

import scripts.import_real_data_to_queue as b3
from app.crawlers.research.transformer import SYSTEM_USER_ID, ResearchTransformer
from app.database import Base, SessionLocal, engine
from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews
from app.models.user import User

logger = logging.getLogger(__name__)

# 与 B3 import_real_data_to_queue.py 的 SOURCE_REGISTRY 分组保持一致：
# bilibili 组 → B 站经验贴；web/school/community 组 → 网页文章类文本
BILIBILI_GROUPS = {"bilibili"}
WEB_GROUPS = {"web", "school", "community"}


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def _load_group_items(groups: set[str]) -> list[dict]:
    """按 B3 SOURCE_REGISTRY 读取真实数据文件并适配为 transformer 可用条目。"""
    items: list[dict] = []
    for filename, subkey, group, *_rest, adapter in b3.SOURCE_REGISTRY:
        if group not in groups:
            continue
        rows = b3._load_rows(filename, subkey)
        items.extend(adapter(rows))
    logger.info("从 real_data/ 读取 %d 条原始记录（分组 %s）", len(items), sorted(groups))
    return items


def _load_bilibili_items() -> list[dict]:
    return _load_group_items(BILIBILI_GROUPS)


def _load_web_items() -> list[dict]:
    return _load_group_items(WEB_GROUPS)


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
        db.query(ExperiencePost.id).filter(ExperiencePost.source_url == source_url).first()
        is not None
    )


def _kaoyan_news_exists(db: Session, source_url: str) -> bool:
    if not source_url:
        return False
    return db.query(KaoyanNews.id).filter(KaoyanNews.source_url == source_url).first() is not None


def _import_experience_posts(db: Session, payloads: list[dict], approve: bool = False) -> int:
    """将清洗后的经验贴 payload 写入 ExperiencePost，返回新增条数。"""
    target_status = "approved" if approve else "pending"
    count = 0
    for payload in payloads:
        source_url = payload.get("source_url", "")
        if not source_url:
            # 真实性门禁（ck_source_gate_experience_posts）：无溯源内容不入库
            continue
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
        if not source_url:
            # 真实性门禁同规则：无溯源内容不入库
            continue
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
    """将 B站 真实数据导入数据库，返回新增经验贴条数。"""
    _ensure_system_user(db)
    payloads = ResearchTransformer.transform_bilibili(items)
    return _import_experience_posts(db, payloads, approve=approve)


def import_web_research(db: Session, items: list[dict], approve: bool = False) -> int:
    """将网页文章真实数据导入数据库，返回新增经验贴条数。"""
    _ensure_system_user(db)
    payloads = ResearchTransformer.transform_web(items)
    return _import_experience_posts(db, payloads, approve=approve)


def import_rss_research(db: Session, items: list[dict], approve: bool = False) -> int:
    """RSS 资讯导入（兼容入口）。

    B1 合规收口后 rss_news_crawler 不再落盘，直接走 store_research_items 入审核队列，
    real_data/ 下也没有 RSS 数据文件；此处保留签名但记录提示后返回 0。
    """
    logger.info("RSS 渠道无落盘数据：rss_news_research 已改直接入审核队列（B1 合规收口），跳过")
    return 0


def seed_from_research(db: Session, approve: bool = False) -> dict[str, int]:
    """读取 real_data/ 真实数据并注入数据库。返回新增数量统计。"""
    # 确保模型对应的表已存在（开发模式；生产环境应通过 Alembic 迁移）
    Base.metadata.create_all(bind=engine)
    _ensure_system_user(db)

    bilibili_items = _load_bilibili_items()
    web_items = _load_web_items()

    transformed_bilibili = ResearchTransformer.transform_bilibili(bilibili_items)
    transformed_web = ResearchTransformer.transform_web(web_items)

    stats = {
        "experience_posts": _import_experience_posts(
            db, transformed_bilibili + transformed_web, approve=approve
        ),
        "kaoyan_news": _import_kaoyan_news(db, [], approve=approve),
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
            "注入完成：新增 %d 条经验贴（B站+网页+院校+社区）",
            stats["experience_posts"],
        )
        print(f"注入完成：新增 {stats['experience_posts']} 条经验贴")
    except Exception as e:
        logger.exception("注入失败: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
