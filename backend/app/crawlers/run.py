"""爬虫CLI运行器。

用法:
    python -m app.crawlers.run --all              # 运行所有爬虫
    python -m app.crawlers.run --source yanzhao   # 运行指定爬虫
    python -m app.crawlers.run --category grad    # 运行指定分类
    python -m app.crawlers.run --all --dry-run    # 试运行（不入库）
"""
import argparse
import sys
import logging
from datetime import datetime, timezone

# 导入注册表（触发所有爬虫的 @register_crawler 装饰器）
# 注意：具体爬虫模块在后续Task中创建，这里先导入空的
from app.crawlers.registry import list_crawlers, list_crawlers_by_category, get_crawler
from app.crawlers.crawler_config import load_config
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("crawler_runner")

def run_crawler(name: str, dry_run: bool = False):
    """运行单个爬虫。"""
    cls = get_crawler(name)
    if not cls:
        logger.error(f"爬虫 '{name}' 未注册")
        return {"status": "not_found", "source_name": name}
    
    config = load_config(name)
    crawler = cls(config=config)
    
    started_at = datetime.now(timezone.utc)
    logger.info(f"=== 开始执行: {name} ({crawler.category}) ===")
    
    if dry_run:
        # 试运行：只fetch和parse，不store
        try:
            raw = crawler.fetch()
            parsed = crawler.parse(raw)
            result = {"status": "dry_run", "fetched": len(raw), "parsed": len(parsed)}
        except Exception as e:
            result = {"status": "failed", "error": str(e)}
    else:
        db = SessionLocal()
        try:
            result = crawler.run(db=db)
        finally:
            db.close()
    
    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()
    result["source_name"] = name
    result["category"] = crawler.category
    result["started_at"] = started_at.isoformat()
    result["finished_at"] = finished_at.isoformat()
    result["duration_seconds"] = round(duration, 1)
    
    logger.info(f"=== 完成: {name} | {result.get('status')} | 耗时 {duration:.1f}s ===")
    return result

def main():
    parser = argparse.ArgumentParser(description="数据爬虫运行器")
    parser.add_argument("--all", action="store_true", help="运行所有已注册爬虫")
    parser.add_argument("--source", type=str, help="运行指定名称的爬虫")
    parser.add_argument("--category", type=str, choices=["grad", "civil", "career", "reports", "research"], help="运行指定分类的爬虫")
    parser.add_argument("--dry-run", action="store_true", help="试运行（不入库）")
    args = parser.parse_args()
    
    if not any([args.all, args.source, args.category]):
        parser.print_help()
        sys.exit(1)
    
    results = []
    
    if args.source:
        results.append(run_crawler(args.source, dry_run=args.dry_run))
    elif args.category:
        crawlers = list_crawlers_by_category(args.category)
        if not crawlers:
            logger.warning(f"分类 '{args.category}' 下无已注册爬虫")
        for name in crawlers:
            results.append(run_crawler(name, dry_run=args.dry_run))
    elif args.all:
        crawlers = list_crawlers()
        if not crawlers:
            logger.warning("无已注册爬虫，请先创建爬虫模块")
        for name in crawlers:
            results.append(run_crawler(name, dry_run=args.dry_run))
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("爬取汇总")
    print("=" * 60)
    for r in results:
        status = r.get("status", "unknown")
        name = r.get("source_name", "?")
        fetched = r.get("fetched", 0)
        stored = r.get("stored", 0)
        print(f"  {name:20s} | {status:10s} | 抓取:{fetched:>6} | 入库:{stored:>6}")
    print("=" * 60)

if __name__ == "__main__":
    main()
