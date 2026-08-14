"""运行所有新爬虫并将数据入库。

【已禁用 — B1 合规收口】本脚本直写业务表（dark_knowledge / forum_experience /
adjustment_real / admission_ratio / retest_experience），绕过 PENDING 审核队列，
与"外部数据仅人工确认入库"的合规红线冲突，默认拒绝执行。

如需在本地开发环境强制运行（不推荐），设置环境变量：
    GRADPATH_ALLOW_LEGACY_SEED=1 python -m app.seed.run_all_new_crawlers

生产数据请改用导入脚本把真实数据写入审核队列（PENDING）后人工确认。
"""
import os
import sys

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.crawlers.grad.dark_knowledge_crawler import DarkKnowledgeCrawler
from app.crawlers.grad.forum_experience_crawler import ForumExperienceCrawler
from app.crawlers.grad.adjustment_real_crawler import AdjustmentRealCrawler
from app.crawlers.grad.admission_ratio_crawler import AdmissionRatioCrawler
from app.crawlers.grad.retest_experience_crawler import RetestExperienceCrawler

_LEGACY_DISABLED_MSG = (
    "[BLOCKED] run_all_new_crawlers 已禁用（B1 合规收口）："
    "本脚本直写业务表，绕过 PENDING 审核队列。"
    "请改用导入脚本写审核队列（人工确认后入库）；"
    "若确需强制运行，设置 GRADPATH_ALLOW_LEGACY_SEED=1。"
)


def run_crawler(crawler_class, db):
    """运行单个爬虫并返回新增条数。"""
    crawler = crawler_class()
    name = crawler.name
    try:
        raw = crawler.fetch()
        parsed = crawler.parse(raw)
        new_count = crawler.store(parsed, db)
        print(f"[OK] {name}: 获取 {len(raw)} 条, 新增 {new_count} 条")
        return new_count
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return 0


def main():
    """主函数：默认拒绝执行（合规收口），除非显式设置环境变量放行。"""
    if os.environ.get("GRADPATH_ALLOW_LEGACY_SEED") != "1":
        print(_LEGACY_DISABLED_MSG)
        sys.exit(1)

    print("=" * 60)
    print("警告：以 legacy 模式运行直写业务表的旧爬虫（仅限本地开发）")
    print("=" * 60)

    db = SessionLocal()
    total_new = 0

    try:
        # 1. 暗知识爬虫
        total_new += run_crawler(DarkKnowledgeCrawler, db)

        # 2. 论坛经验贴爬虫
        total_new += run_crawler(ForumExperienceCrawler, db)

        # 3. 调剂信息爬虫
        total_new += run_crawler(AdjustmentRealCrawler, db)

        # 4. 报录比爬虫
        total_new += run_crawler(AdmissionRatioCrawler, db)

        # 5. 复试经验爬虫
        total_new += run_crawler(RetestExperienceCrawler, db)

        print("=" * 60)
        print(f"全部完成！共新增 {total_new} 条数据")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
