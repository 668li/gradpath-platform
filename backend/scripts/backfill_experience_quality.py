"""一次性回填脚本：为存量经验贴补齐 Phase G 提纯字段。

适用：迁移前已入库的 experience_posts（quality_score/quality_grade/
is_promotion/promotion_confidence/promotion_reason/structured_meta 为 NULL
或缺失）。调用与 research_promote 相同的打分器/反软广/结构化抽取，
保证与审核链路（新落库条目）行为一致。

幂等：已存在 quality_grade 的行跳过（审核链路新落库的带分条目不重复算）。
走应用 ORM + 参数绑定，无 SQL 拼接；只 UPDATE 单条 id，不批量硬编码。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.crawlers.research.experience_quality import (
    detect_promotion,
    extract_experience_meta,
    score_experience_item,
)
from app.database import SessionLocal
from app.models.experience_post import ExperiencePost


def main() -> None:
    with SessionLocal() as db:
        rows = (
            db.query(ExperiencePost)
            .filter(ExperiencePost.quality_grade.is_(None))
            .all()
        )
        if not rows:
            print("无待回填经验贴（全部已有质量分）")
            return
        print(f"待回填: {len(rows)} 条")
        for post in rows:
            is_promotion, promo_conf, promo_reason = detect_promotion(
                post.title or "", post.content or "", post.tags
            )
            score, grade = score_experience_item(
                title=post.title or "",
                content=post.content or "",
                source_platform=post.source_platform or "user",
                source_url=post.source_url or "",
                external_view_count=post.external_view_count or 0,
                external_like_count=post.external_like_count or 0,
                is_promotion=is_promotion,
            )
            post.quality_score = int(score)
            post.quality_grade = grade
            post.is_promotion = is_promotion
            post.promotion_confidence = promo_conf
            post.promotion_reason = promo_reason
            post.structured_meta = extract_experience_meta(
                post.title or "", post.content or "", post.tags
            )
        db.commit()
        print(f"完成: {len(rows)} 条已回填")


if __name__ == "__main__":
    main()
