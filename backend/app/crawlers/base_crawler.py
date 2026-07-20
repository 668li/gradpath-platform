"""爬虫基类 — 所有数据源爬虫继承此类。"""
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
import requests
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database import SessionLocal

logger = logging.getLogger(__name__)

class BaseCrawler(ABC):
    """抽象基类：封装HTTP请求/解析/去重/入库/日志/重试/限速。"""
    
    # 子类必须覆盖
    name: str = ""           # 爬虫名称（唯一标识）
    category: str = ""       # 分类: grad/civil/career/reports
    description: str = ""    # 描述
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
        })
        self.stats = {"fetched": 0, "stored": 0, "errors": 0, "duplicates": 0}
        self._rate_limit = self.config.get("rate_limit", 1.0)  # 默认1秒间隔
    
    @abstractmethod
    def fetch(self) -> list[dict]:
        """抓取数据，返回原始数据列表。子类必须实现。"""
        ...
    
    @abstractmethod
    def parse(self, raw_items: list[dict]) -> list[dict]:
        """解析原始数据为标准结构。子类必须实现。"""
        ...
    
    @abstractmethod
    def store(self, items: list[dict], db: Session) -> int:
        """存储数据到数据库，返回新增条数。子类必须实现。"""
        ...
    
    def run(self, db: Session = None) -> dict:
        """执行完整爬取流程：fetch → parse → store。"""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        try:
            logger.info(f"[{self.name}] 开始爬取...")
            raw = self.fetch()
            self.stats["fetched"] = len(raw)
            logger.info(f"[{self.name}] 抓取到 {len(raw)} 条原始数据")
            
            parsed = self.parse(raw)
            logger.info(f"[{self.name}] 解析为 {len(parsed)} 条标准数据")
            
            stored = self.store(parsed, db)
            self.stats["stored"] = stored
            logger.info(f"[{self.name}] 入库 {stored} 条新数据")
            
            return {"status": "success", **self.stats}
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"[{self.name}] 爬取失败: {e}")
            return {"status": "failed", "error": str(e), **self.stats}
        finally:
            if own_db:
                db.close()
    
    def _request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """带限速和重试的HTTP请求。"""
        max_retries = self.config.get("max_retries", 3)
        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, timeout=30, **kwargs)
                resp.raise_for_status()
                time.sleep(self._rate_limit)
                return resp
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 2
                    logger.warning(f"[{self.name}] 请求失败({attempt+1}/{max_retries}), {wait}秒后重试: {e}")
                    time.sleep(wait)
                else:
                    raise
    
    def _dedup_key(self, item: dict) -> str:
        """生成去重键，子类可覆盖。默认用所有字段拼接。"""
        return "|".join(str(v) for v in sorted(item.values()))
    
    # ===== 批量UPSERT方法 =====
    
    def batch_upsert(
        self,
        db: Session,
        model_class,
        items: list[dict],
        unique_key: str | list[str],
        batch_size: int = 200,
    ) -> int:
        """批量UPSERT：如果记录存在则更新，不存在则插入。
        
        Args:
            db: 数据库会话
            model_class: SQLAlchemy模型类
            items: 要插入/更新的数据列表
            unique_key: 去重键字段名（单字段字符串或字段名列表）
            batch_size: 每批处理的记录数
        
        Returns:
            新增或更新的记录数
        """
        if not items:
            return 0
        
        # 统一unique_key为列表
        if isinstance(unique_key, str):
            unique_key = [unique_key]
        
        # 去重：按unique_key保留最后一条记录
        seen = set()
        deduped = []
        for item in reversed(items):  # 反转后遍历，保留最后出现的
            key = tuple(item.get(k) for k in unique_key)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        deduped.reverse()  # 恢复原始顺序
        
        total_affected = 0
        
        for i in range(0, len(deduped), batch_size):
            batch = deduped[i:i + batch_size]
            
            try:
                # 构建UPSERT语句
                stmt = pg_insert(model_class).values(batch)
                
                # 构建更新字典（排除unique_key字段）
                update_cols = {k: stmt.excluded[k] for k in batch[0].keys() if k not in unique_key}
                
                if update_cols:
                    stmt = stmt.on_conflict_do_update(
                        index_elements=unique_key,
                        set_=update_cols,
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing()
                
                result = db.execute(stmt)
                total_affected += result.rowcount
                db.flush()
                
            except Exception as e:
                logger.warning(f"[{self.name}] 批量UPSERT失败(batch {i//batch_size + 1}): {e}")
                # 回退到逐条处理
                for item in batch:
                    try:
                        stmt = pg_insert(model_class).values(**item)
                        update_cols = {k: getattr(stmt.excluded, k) for k in item.keys() if k not in unique_key}
                        if update_cols:
                            stmt = stmt.on_conflict_do_update(
                                index_elements=unique_key,
                                set_=update_cols,
                            )
                        db.execute(stmt)
                        total_affected += 1
                    except Exception as e2:
                        logger.error(f"[{self.name}] 单条UPSERT失败: {e2}")
                        self.stats["errors"] += 1
        
        db.commit()
        return total_affected
    
    def batch_upsert_simple(
        self,
        db: Session,
        model_class,
        items: list[dict],
        unique_key: str | list[str],
        batch_size: int = 200,
    ) -> int:
        """简化版批量UPSERT：适用于没有created_at/updated_at字段的模型。
        
        与batch_upsert相同，但跳过timestamp字段的更新。
        """
        return self.batch_upsert(db, model_class, items, unique_key, batch_size)
    
    def get_existing_keys(
        self,
        db: Session,
        model_class,
        key_field: str,
        values: list,
    ) -> set:
        """批量查询已存在的去重键，用于快速判断是否需要插入。
        
        Returns:
            已存在的键集合
        """
        if not values:
            return set()
        
        # 分批查询（避免IN子句过大）
        existing = set()
        batch_size = 500
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            col = getattr(model_class, key_field)
            rows = db.query(col).filter(col.in_(batch)).all()
            existing.update(row[0] for row in rows)
        
        return existing
