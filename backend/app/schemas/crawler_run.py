"""爬虫执行日志 Schema。"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CrawlerRunResponse(BaseModel):
    id: UUID
    source_name: str
    category: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: int = 0
    items_fetched: int = 0
    items_stored: int = 0
    items_duplicates: int = 0
    error_count: int = 0
    error_message: str | None = None
    log: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrawlerInfo(BaseModel):
    """爬虫信息。"""
    name: str
    category: str
    description: str
    config: dict = {}


class CrawlerRunRequest(BaseModel):
    """触发爬虫请求。"""
    source_name: str
    dry_run: bool = False
