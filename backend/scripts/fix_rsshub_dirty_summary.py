"""修复 rsshub 来源脏数据（2026-08-16）：RSSHub summary 为 HTML 片段且超 500 字符。

根因：_extract_text 只取字符串不清洗 HTML，RSSHub 的 summary 原样入库，
导致 KaoyanNewsResponse.summary(max_length=500) 校验失败 → 资讯中心 API 500。

修复：仅对 source_platform='rsshub' 的 kaoyan_news 行，复用
ResearchTransformer._strip_html/_clean_text 清洗 title/summary/content，
summary 截断 500（与 transformer.transform_rss 语义一致）。幂等可重跑。

运行：DATABASE_URL=sqlite:///D:/职业规划/职业规划/backend/gradpath.db \
      py -3.13 scripts/fix_rsshub_dirty_summary.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.crawlers.research.transformer import ResearchTransformer
from app.database import SessionLocal

SUMMARY_MAX = 500
TITLE_MAX = 200


def main() -> None:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT id, title, summary, content FROM kaoyan_news "
                "WHERE source_platform = 'rsshub'"
            )
        ).fetchall()
        fixed_summary = fixed_content = fixed_title = fixed = 0
        for rid, title, summary, content in rows:
            new_title = ResearchTransformer._clean_text(
                ResearchTransformer._strip_html(title)
            )[:TITLE_MAX]
            new_summary = None
            if summary:
                new_summary = ResearchTransformer._clean_text(
                    ResearchTransformer._strip_html(summary)
                )[:SUMMARY_MAX]
                if new_summary != summary:
                    fixed_summary += 1
            new_content = None
            if content:
                new_content = ResearchTransformer._clean_text(
                    ResearchTransformer._strip_html(content)
                )
                if new_content != content:
                    fixed_content += 1
            if new_title != title:
                fixed_title += 1
            if (new_title, new_summary, new_content) == (title, summary, content):
                continue
            db.execute(
                text(
                    "UPDATE kaoyan_news SET title = :t, summary = :s, content = :c "
                    "WHERE id = :rid"
                ),
                {"t": new_title, "s": new_summary, "c": new_content, "rid": rid},
            )
            fixed += 1
        db.commit()
        print(
            f"rsshub 行 {len(rows)} | 修复 {fixed}（title {fixed_title}"
            f" / summary {fixed_summary} / content {fixed_content}）"
        )


if __name__ == "__main__":
    main()
