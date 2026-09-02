"""S2: 存量清理——对所有 is_off_topic IS NULL 的 experience_posts 跑主题分类。

用法:
  docker cp scripts/s2_batch_topic_classify.py gradpath-prod-backend-1:/tmp/
  docker exec gradpath-prod-backend-1 python /tmp/s2_batch_topic_classify.py
"""

import logging
import sys
from pathlib import Path

# 确保能导入 app 模块
sys.path.insert(0, "/app")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("s2_batch_classify")

from app.crawlers.research.transformer import classify_topic_relevance
from app.database import SessionLocal
from app.models.experience_post import ExperiencePost


def main():
    db = SessionLocal()
    try:
        posts = (
            db.query(ExperiencePost)
            .filter(ExperiencePost.is_off_topic.is_(None))
            .all()
        )
        logger.info("共 %d 条待分类", len(posts))

        count_off = 0
        count_on = 0
        count_amb = 0
        batch = []
        for p in posts:
            title = p.title or ""
            content = p.content or ""
            tags = [t for t in (p.tags or []) if isinstance(t, str)]
            is_off, reason, domain = classify_topic_relevance(title, content, tags)
            # 三态：True=离题；None=无强锚点也无领域词（存疑）→ 落 False 保持可见并定稿，
            # 避免每次重跑都重复分类这批无领域信号内容（它们由人工/feed 审核决定是否移除）。
            flag = False if is_off is None else is_off
            p.is_off_topic = flag
            p.topic_reason = reason if is_off else None
            p.topic_domain = domain
            batch.append(p)
            if is_off is True:
                count_off += 1
                if count_off <= 10:
                    logger.info(
                        "  [离题] %s — %s（domain=%s）",
                        title[:50],
                        reason,
                        domain,
                    )
            elif is_off is None:
                count_amb += 1
                if count_amb <= 8:
                    logger.info(
                        "  [存疑放行] %s — %s",
                        title[:50],
                        reason,
                    )
            else:
                count_on += 1
                if count_on <= 5:
                    logger.info(
                        "  [正常] %s — domain=%s", title[:50], domain
                    )

            # 每 500 条提交一次
            if len(batch) >= 500:
                db.commit()
                logger.info("  已提交 %d 条", len(batch))
                batch = []

        if batch:
            db.commit()
            logger.info("  最终提交 %d 条", len(batch))

        logger.info(
            "=== S2 完成 === 总计 %d | 离题 %d | 存疑放行 %d | 正常 %d",
            len(posts),
            count_off,
            count_amb,
            count_on,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()