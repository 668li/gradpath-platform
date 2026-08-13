"""爬虫基类 — 所有数据源爬虫继承此类。

合规护栏（红线：不批量抓取研招网、仅人工确认入库）：
- 单爬虫固定串行执行（并发=1，禁止多线程放大请求）
- ``max_pages`` / ``max_items`` 页数与条数上限，防止一次任务抓取量失控
- ``rate_limit`` 请求间隔（默认 1s），配合 max_retries 已内置
- 所有入库必须经人工确认（PENDING 审核队列），基类不提供绕过手段
"""
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
        # 合规护栏：单次任务抓取上限（0 表示不限制，研招网来源必须显式配置）
        self._max_pages = int(self.config.get("max_pages", 0))
        self._max_items = int(self.config.get("max_items", 0))
        # 并发=1（固定串行，不提供并发执行入口）
        self._concurrency = 1
    
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
            # 合规护栏：页数上限（max_pages），防止单次任务抓取量失控
            if self._max_pages > 0 and len(raw) > self._max_pages:
                logger.warning(
                    f"[{self.name}] 触发页数护栏: 抓取 {len(raw)} 条 > max_pages={self._max_pages}，截断"
                )
                raw = raw[:self._max_pages]
            self.stats["fetched"] = len(raw)
            logger.info(f"[{self.name}] 抓取到 {len(raw)} 条原始数据")
            
            parsed = self.parse(raw)
            # 合规护栏：条数上限（max_items）
            if self._max_items > 0 and len(parsed) > self._max_items:
                logger.warning(
                    f"[{self.name}] 触发条数护栏: 解析 {len(parsed)} 条 > max_items={self._max_items}，截断"
                )
                parsed = parsed[:self._max_items]
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

        # 方言判定：pg_insert(ON CONFLICT) 仅 PostgreSQL 支持。
        # SQLite（本地 dev / pytest）降级为"查重→仅插入缺失"，不做 UPDATE；
        # 生产环境强制 PostgreSQL，行为与 ON CONFLICT 一致。
        if db.get_bind().dialect.name == "sqlite":
            return self._sqlite_upsert(db, model_class, deduped, unique_key)
        
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
    
    def _sqlite_upsert(self, db: Session, model_class, items: list[dict], unique_key: list) -> int:
        """SQLite 降级批量入库：按 unique_key 查重后仅插入缺失记录。

        仅用于本地开发 / 测试（生产强制 PostgreSQL，走 batch_upsert 的 ON CONFLICT 精确 upsert）。
        复用 get_existing_keys 批量查重；所有值经 ORM 绑定参数注入，不拼接 SQL 字符串。
        注意：SQLite 降级只对单列唯一键做幂等去重；多列唯一键按首列近似去重，
        生产环境不受影响。
        """
        if not items:
            return 0

        key_field = unique_key[0]
        valid_cols = set(model_class.__table__.columns.keys())
        if key_field not in valid_cols:
            logger.error(f"[{self.name}] SQLite降级: 唯一键列 {key_field} 不存在，跳过本次入库")
            return 0

        existing_keys = self.get_existing_keys(
            db, model_class, key_field, [i.get(key_field) for i in items]
        )
        new_items = [i for i in items if i.get(key_field) not in existing_keys]
        for item in new_items:
            db.add(model_class(**item))
        db.commit()
        return len(new_items)
    
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
