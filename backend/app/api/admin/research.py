"""管理员外部调研 API — 触发爬虫、导入数据、审核内容。"""
import json
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.crawlers.research.bilibili_research_crawler import BilibiliResearchCrawler
from app.crawlers.research.rss_news_crawler import RssNewsCrawler
from app.database import get_db
from app.models.crawler_run import CrawlerRun
from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews
from app.models.user import User
from app.schemas.research_admin import (
    BilibiliResearchRequest,
    ResearchApproveRequest,
    ResearchPendingItem,
    ResearchPendingListResponse,
    ResearchTriggerResponse,
    RssResearchRequest,
)
from app.seed.seed_from_research import import_bilibili_research, import_rss_research

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/research", tags=["管理员-外部调研"])


def _create_run_record(
    db: Session,
    source_name: str,
    admin: User,
    details: dict,
) -> CrawlerRun:
    """创建 CrawlerRun 操作日志记录。"""
    record = CrawlerRun(
        source_name=source_name,
        category="research_admin",
        status="running",
        log=json.dumps(
            {
                "admin_id": str(admin.id),
                "admin_email": admin.email,
                **details,
            },
            ensure_ascii=False,
        ),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _finish_run_record(
    db: Session,
    record: CrawlerRun,
    status: str,
    fetched: int = 0,
    stored: int = 0,
    error: str | None = None,
) -> None:
    """更新 CrawlerRun 记录为完成状态。"""
    record.status = status
    record.items_fetched = fetched
    record.items_stored = stored
    if error:
        record.error_message = error
    db.commit()


@router.post("/bilibili", response_model=ResearchTriggerResponse)
def run_bilibili_research(
    body: BilibiliResearchRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """触发 B站调研并导入数据库。"""
    run_record = _create_run_record(
        db,
        "bilibili_research",
        admin,
        {
            "platform": "bilibili",
            "keyword": body.keyword,
            "pages": body.pages,
            "auto_approve": body.auto_approve,
        },
    )

    try:
        crawler = BilibiliResearchCrawler(
            config={"keyword": body.keyword, "pages": body.pages}
        )
        raw_items = crawler.fetch()
        parsed_items = crawler.parse(raw_items)
        crawler.store(parsed_items, db)

        imported = import_bilibili_research(db, parsed_items, approve=body.auto_approve)

        _finish_run_record(
            db,
            run_record,
            status="success",
            fetched=len(raw_items),
            stored=imported,
        )

        logger.info(
            "[research_admin] admin=%s platform=bilibili keyword=%s imported=%d",
            admin.id,
            body.keyword,
            imported,
        )

        return ResearchTriggerResponse(
            status="success",
            fetched=len(raw_items),
            stored=imported,
            pending=0 if body.auto_approve else imported,
        )
    except Exception as e:
        logger.exception("[research_admin] B站调研失败: %s", e)
        _finish_run_record(
            db,
            run_record,
            status="failed",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="调研执行失败，请查看服务器日志",
        )


@router.post("/rss", response_model=ResearchTriggerResponse)
def run_rss_research(
    body: RssResearchRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """触发 RSS 调研并导入数据库。"""
    output_path = Path(tempfile.gettempdir()) / "rss_news_research.json"
    config: dict[str, object] = {"output_path": str(output_path)}
    if body.feeds:
        config["feeds"] = body.feeds
    if body.keywords:
        config["keywords"] = body.keywords

    run_record = _create_run_record(
        db,
        "rss_news_research",
        admin,
        {
            "platform": "rss",
            "feeds": body.feeds,
            "keywords": body.keywords,
            "auto_approve": body.auto_approve,
        },
    )

    try:
        crawler = RssNewsCrawler(config=config)
        raw_items = crawler.fetch()
        parsed_items = crawler.parse(raw_items)
        crawler.store(parsed_items, db)

        imported = import_rss_research(db, parsed_items, approve=body.auto_approve)

        _finish_run_record(
            db,
            run_record,
            status="success",
            fetched=len(raw_items),
            stored=imported,
        )

        logger.info(
            "[research_admin] admin=%s platform=rss imported=%d",
            admin.id,
            imported,
        )

        return ResearchTriggerResponse(
            status="success",
            fetched=len(raw_items),
            stored=imported,
            pending=0 if body.auto_approve else imported,
        )
    except Exception as e:
        logger.exception("[research_admin] RSS调研失败: %s", e)
        _finish_run_record(
            db,
            run_record,
            status="failed",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="调研执行失败，请查看服务器日志",
        )


@router.get("/pending", response_model=ResearchPendingListResponse)
def list_pending_research_items(
    platform: str | None = Query(None, description="来源平台: bilibili / web / rss"),
    type: str | None = Query(None, description="类型: experience / news"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取待审核的外部经验贴和资讯列表。"""
    if platform and platform not in ("bilibili", "web", "rss"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="platform 必须是 bilibili / web / rss 之一",
        )
    if type and type not in ("experience", "news"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="type 必须是 experience / news 之一",
        )

    items: list[ResearchPendingItem] = []

    start = (page - 1) * page_size
    fetch_limit = start + page_size

    if type is None or type == "experience":
        exp_query = db.query(ExperiencePost).filter(ExperiencePost.status == "pending")
        if platform:
            exp_query = exp_query.filter(ExperiencePost.source_platform == platform)
        exp_total = exp_query.count()
        for post in (
            exp_query.order_by(ExperiencePost.created_at.desc()).limit(fetch_limit).all()
        ):
            items.append(
                ResearchPendingItem(
                    id=post.id,
                    title=post.title,
                    summary=post.summary,
                    source_platform=post.source_platform,
                    source_url=post.source_url,
                    status=post.status,
                    item_type="experience",
                    created_at=post.created_at,
                )
            )
    else:
        exp_total = 0

    if type is None or type == "news":
        news_query = db.query(KaoyanNews).filter(KaoyanNews.status == "pending")
        if platform:
            news_query = news_query.filter(KaoyanNews.source_platform == platform)
        news_total = news_query.count()
        for news in (
            news_query.order_by(KaoyanNews.created_at.desc()).limit(fetch_limit).all()
        ):
            items.append(
                ResearchPendingItem(
                    id=news.id,
                    title=news.title,
                    summary=news.summary,
                    source_platform=news.source_platform,
                    source_url=news.source_url,
                    status=news.status,
                    item_type="news",
                    created_at=news.created_at,
                )
            )
    else:
        news_total = 0

    items.sort(key=lambda x: x.created_at, reverse=True)
    total = exp_total + news_total
    paged_items = items[start:start + page_size]

    return ResearchPendingListResponse(
        items=paged_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{item_id}/approve")
def approve_research_item(
    item_id: UUID,
    body: ResearchApproveRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """审核通过指定调研项目。"""
    if body.item_type == "experience":
        item = (
            db.query(ExperiencePost)
            .filter(ExperiencePost.id == item_id, ExperiencePost.status == "pending")
            .first()
        )
    else:
        item = (
            db.query(KaoyanNews)
            .filter(KaoyanNews.id == item_id, KaoyanNews.status == "pending")
            .first()
        )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待审核项目不存在",
        )

    item.status = "approved"
    db.commit()

    _create_run_record(
        db,
        f"{body.item_type}_approve",
        admin,
        {
            "platform": item.source_platform,
            "item_id": str(item_id),
            "item_type": body.item_type,
            "action": "approve",
            "title": item.title,
        },
    )

    return {
        "message": "审核通过",
        "item_id": str(item_id),
        "item_type": body.item_type,
    }


@router.post("/{item_id}/reject")
def reject_research_item(
    item_id: UUID,
    body: ResearchApproveRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """拒绝指定调研项目。"""
    if body.item_type == "experience":
        item = (
            db.query(ExperiencePost)
            .filter(ExperiencePost.id == item_id, ExperiencePost.status == "pending")
            .first()
        )
    else:
        item = (
            db.query(KaoyanNews)
            .filter(KaoyanNews.id == item_id, KaoyanNews.status == "pending")
            .first()
        )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待审核项目不存在",
        )

    item.status = "rejected"
    db.commit()

    _create_run_record(
        db,
        f"{body.item_type}_reject",
        admin,
        {
            "platform": item.source_platform,
            "item_id": str(item_id),
            "item_type": body.item_type,
            "action": "reject",
            "title": item.title,
        },
    )

    return {
        "message": "已拒绝",
        "item_id": str(item_id),
        "item_type": body.item_type,
    }
