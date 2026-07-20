"""运行所有新爬虫并将数据入库。

此脚本依次运行：
1. 暗知识爬虫 (30条)
2. 论坛经验贴爬虫 (10条)
3. 调剂信息爬虫 (90条)
4. 报录比爬虫 (90条)
5. 复试经验爬虫 (30条)

总计约250条新数据。
"""
import sys
import os

# 确保可以导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.crawlers.grad.dark_knowledge_crawler import DarkKnowledgeCrawler
from app.crawlers.grad.forum_experience_crawler import ForumExperienceCrawler
from app.crawlers.grad.adjustment_real_crawler import AdjustmentRealCrawler
from app.crawlers.grad.admission_ratio_crawler import AdmissionRatioCrawler
from app.crawlers.grad.retest_experience_crawler import RetestExperienceCrawler


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
    """主函数：运行所有爬虫。"""
    print("=" * 60)
    print("开始运行所有爬虫...")
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
