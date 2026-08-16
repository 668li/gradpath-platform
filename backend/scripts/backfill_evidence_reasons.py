"""一次性回填脚本：为存量条目补齐 Phase I 证据链/可解释字段。

适用：迁移前已入库、quality_reasons 为 NULL 的行（Phase G 及更早的存量数据）：
  - experience_posts：quality_reasons（逐维扣分原因）+ structured_meta 并入
    evidence/confidence（原文片段/置信度）
  - kaoyan_news：quality_reasons + structured_meta 并入 evidence/confidence/
    effective_year（数据年份）

调用与 research_promote 相同的打分器/结构化抽取，保证与审核链路（新落库条目）
行为一致。质量分/分级沿用同一打分器重算（输入一致 → 输出与 Phase G 回填一致）。

幂等：已存在 quality_reasons 的行跳过（Phase I 审核链路新落库的带原因条目不重算）。
走应用 ORM + 参数绑定，无 SQL 拼接；只 UPDATE 单条 id，不批量硬编码。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.crawlers.research.experience_quality import (
    detect_promotion,
    extract_experience_meta_with_evidence,
    score_experience_item_detailed,
)
from app.crawlers.research.news_meta import extract_news_structured_meta_with_evidence
from app.crawlers.research.quality import score_item_detailed
from app.database import SessionLocal
from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews


def backfill_experience_posts(db) -> int:
    rows = (
        db.query(ExperiencePost)
        .filter(ExperiencePost.quality_reasons.is_(None))
        .all()
    )
    for post in rows:
        title = post.title or ""
        content = post.content or ""
        tags = [t for t in (post.tags or []) if isinstance(t, str)]

        is_promotion, promo_conf, promo_reason = detect_promotion(title, content, tags)
        score_detail = score_experience_item_detailed(
            title=title,
            content=content,
            source_platform=post.source_platform or "user",
            source_url=post.source_url or "",
            external_view_count=post.external_view_count or 0,
            external_like_count=post.external_like_count or 0,
            is_promotion=is_promotion,
            promotion_reason=promo_reason,
        )
        post.quality_score = int(score_detail["score"])
        post.quality_grade = score_detail["grade"]
        post.quality_reasons = score_detail["reasons"]

        structured_meta, evidence, confidence = extract_experience_meta_with_evidence(
            title, content, tags
        )
        post.structured_meta = {
            **structured_meta,
            "evidence": evidence,
            "confidence": confidence,
        }
        # 软广标注（Phase G 已回填过则重算结果一致，缺失则补齐）
        post.is_promotion = is_promotion
        post.promotion_confidence = promo_conf
        post.promotion_reason = promo_reason
    return len(rows)


def backfill_kaoyan_news(db) -> int:
    rows = db.query(KaoyanNews).filter(KaoyanNews.quality_reasons.is_(None)).all()
    for news in rows:
        title = news.title or ""
        content = news.content or ""
        score_detail = score_item_detailed(
            title=title,
            content=content,
            summary=news.summary or "",
            source_url=news.source_url or "",
            published_at=news.published_at,
            crawled_at=news.crawled_at,
        )
        news.quality_score = int(score_detail["score"])
        news.quality_grade = score_detail["grade"]
        news.quality_reasons = score_detail["reasons"]

        structured_meta, evidence, confidence, effective_year = (
            extract_news_structured_meta_with_evidence(title, content)
        )
        news.structured_meta = {
            **structured_meta,
            "evidence": evidence,
            "confidence": confidence,
            "effective_year": effective_year,
        }
    return len(rows)


def main() -> None:
    with SessionLocal() as db:
        exp_count = backfill_experience_posts(db)
        news_count = backfill_kaoyan_news(db)
        if exp_count == 0 and news_count == 0:
            print("无待回填条目（全部已有 quality_reasons）")
            return
        db.commit()
        print(f"完成: 经验贴 {exp_count} 条 / 资讯 {news_count} 条已回填")


if __name__ == "__main__":
    main()
