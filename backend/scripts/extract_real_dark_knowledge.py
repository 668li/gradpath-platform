"""暗知识真实化（2026-08-16）：从已审核的真实外部经验贴提取避坑类暗知识。

背景：dark_knowledge 表原有 73 条合成种子数据已删除（用户拍板「删假换真」）。
本脚本从 experience_posts 中 status='approved' 且 source_platform != 'user' 的
真实爬取经验贴（B 站等，1356 条）中，按避坑/教训关键词筛选，每帖提炼一条暗知识：

  - stage：按帖子分类映射（备考→preparation / 择校→school_selection /
    复试→retest / 调剂→transfer，默认 preparation）
  - title：帖子标题（unique 去重，超长截断）
  - content：真实原文（summary 或 content 前 2000 字）+ 尾行来源标注
  - tags：原帖 tags + 溯源标记 "src:experience_post:{id}"
  - importance：medium（规则提取，不冒充专家判断）

不伪造 common_misconception / actionable_advice / verification_method（留空，
诚实降级）。幂等：title unique 冲突跳过。全 ORM 参数绑定。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.experience_post import ExperiencePost
from app.models.grad_intel import DarkKnowledge

AVOID_KEYWORDS = [
    "避坑", "踩坑", "教训", "劝退", "避雷", "别报", "不要报", "不建议",
    "误区", "后悔", "失败", "翻车", "血泪", "惨败", "陷阱", "千万别",
]

STAGE_MAP = {
    "择校": "school_selection",
    "备考": "preparation",
    "复习": "preparation",
    "心态": "preparation",
    "经验": "preparation",
    "初试": "exam",
    "复试": "retest",
    "调剂": "transfer",
    "避坑": "preparation",
}


def main() -> None:
    with SessionLocal() as db:
        posts = (
            db.query(ExperiencePost)
            .filter(
                ExperiencePost.status == "approved",
                ExperiencePost.source_platform != "user",
            )
            .all()
        )
        matched = 0
        inserted = 0
        skipped = 0
        for p in posts:
            text = f"{p.title or ''} {(p.structured_meta or {}).get('summary', '')}"
            hay = f"{p.title or ''} {p.content or ''}"
            if not any(k in hay for k in AVOID_KEYWORDS):
                continue
            matched += 1
            title = (p.title or "").strip()[:200]
            if not title:
                skipped += 1
                continue
            exists = db.query(DarkKnowledge.id).filter(DarkKnowledge.title == title).first()
            if exists:
                skipped += 1
                continue
            content = (p.summary or (p.content or "")[:2000]).strip()
            source_line = f"\n\n来源：真实经验贴（{p.source_platform}）{p.source_url or ''}"
            category = (p.category or "避坑")[:100]
            stage = STAGE_MAP.get(category, "preparation")
            tags = [t for t in (p.tags or []) if isinstance(t, str)][:8]
            tags.append(f"src:experience_post:{p.id}")
            db.add(
                DarkKnowledge(
                    stage=stage,
                    category=category,
                    title=title,
                    content=content + source_line,
                    importance="medium",
                    tags=tags,
                )
            )
            inserted += 1
        db.commit()
        print(f"真实经验贴总数: {len(posts)} | 命中避坑关键词: {matched} | 入库暗知识: {inserted} | 跳过(空标题/重复): {skipped}")


if __name__ == "__main__":
    main()
