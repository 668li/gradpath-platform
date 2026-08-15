"""AI 相关 Celery 任务 — 异步生成 AI 建议、批量处理长任务。

任务路由：app.tasks.ai_tasks.* → ai 队列
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ai_tasks.generate_ai_advice_async")
def generate_ai_advice_async(user_id: str, decision_id: str):
    """异步生成 AI 建议（不阻塞 HTTP 请求）。

    用途：用户提交决策后立即返回 202，后台异步调用 LLM 生成建议，
    完成后通过 WebSocket 推送给用户。

    Args:
        user_id: 用户 ID（字符串形式的 UUID）
        decision_id: 决策 ID（字符串形式的 UUID）
    """
    try:
        user_uuid = UUID(user_id)
        decision_uuid = UUID(decision_id)
    except (ValueError, TypeError) as e:
        logger.error("AI 任务参数解析失败: user_id=%s decision_id=%s: %s", user_id, decision_id, e)
        return {"status": "failed", "error": "invalid uuid"}

    db = SessionLocal()
    try:
        # 延迟导入避免循环依赖
        from app.services.decision_advice_service import generate_advice_for_decision
        from app.core.websocket_manager import manager as ws_manager

        advice = generate_advice_for_decision(db, user_uuid, decision_uuid)

        # 推送结果给前端
        try:
            ws_manager.send_personal_sync(str(user_uuid), {
                "type": "ai_advice_ready",
                "decision_id": str(decision_uuid),
                "advice": advice,
            })
        except Exception as e:
            logger.warning("AI 建议推送失败: %s", e)

        return {"status": "success", "advice": advice}
    except Exception as e:
        logger.error("AI 建议生成失败 user=%s decision=%s: %s", user_id, decision_id, e)
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.ai_tasks.batch_generate_advice")
def batch_generate_advice(decision_ids: list[str], user_id: str):
    """批量生成多决策的 AI 建议（队列内部串行处理，避免 LLM 配额瞬时打满）。

    Args:
        decision_ids: 决策 ID 列表（字符串形式 UUID）
        user_id: 用户 ID
    """
    results: list[dict] = []
    for did in decision_ids:
        result = generate_ai_advice_async.run(user_id, did)
        results.append({"decision_id": did, "result": result})
    return results


@celery_app.task(name="app.tasks.ai_tasks.enhance_kaoyan_news_batch")
def enhance_kaoyan_news_batch(limit: int = 5):
    """批量增强考研资讯（Phase C2）：LLM 生成 ai_summary + 精确 key_dates。

    串行处理已审核入库且缺 ai_summary 的资讯（按质量分降序），单条失败
    自动降级保留规则版结果（research_promote 落库时已算），不影响其他条目。

    Args:
        limit: 单批最多增强条数（默认 5，避免 LLM 配额瞬时打满）
    """
    db = SessionLocal()
    try:
        from app.models.kaoyan_news import KaoyanNews
        from app.services.news_enhance import enhance_news_item

        rows = (
            db.query(KaoyanNews)
            .filter(
                KaoyanNews.status == "approved",
                KaoyanNews.ai_summary.is_(None),
            )
            .order_by(KaoyanNews.quality_score.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            logger.info("[news_enhance] 无待增强资讯（limit=%d）", limit)
            return {"status": "skipped", "enhanced": 0, "degraded": 0}

        import asyncio

        enhanced = degraded = 0
        for news in rows:
            try:
                result = asyncio.run(enhance_news_item(db, news))
            except Exception as e:  # noqa: BLE001
                logger.warning("[news_enhance] 单条增强异常降级 %s: %s", news.id, e)
                result = {"status": "degraded"}
            if result.get("status") == "enhanced":
                enhanced += 1
            else:
                degraded += 1
            # 逐条提交：单条失败不回滚整批
            db.commit()

        logger.info("[news_enhance] 批量完成 enhanced=%d degraded=%d", enhanced, degraded)
        return {"status": "success", "enhanced": enhanced, "degraded": degraded}
    except Exception as e:
        logger.error("[news_enhance] 批量增强失败: %s", e)
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.ai_tasks.enhance_experience_post_batch")
def enhance_experience_post_batch(limit: int = 5):
    """批量增强考研经验贴（Phase G 挂载点）：LLM 生成 ai_summary + 分类修正。

    串行处理已审核入库且缺 ai_summary 的外部经验贴（按质量分降序），
    单条失败自动降级保留规则版结果（research_promote 落库时已算），
    不影响其他条目。默认不投递（schedule_experience_enhancement 以
    LLM_API_KEY + REDIS_URL 为 gate），配好 key 后自动启用。

    Args:
        limit: 单批最多增强条数（默认 5）
    """
    db = SessionLocal()
    try:
        from app.models.experience_post import ExperiencePost
        from app.services.experience_enhance import enhance_experience_item

        rows = (
            db.query(ExperiencePost)
            .filter(
                ExperiencePost.status == "approved",
                ExperiencePost.ai_summary.is_(None),
                ExperiencePost.source_platform != "user",
            )
            .order_by(ExperiencePost.quality_score.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            logger.info("[experience_enhance] 无待增强经验贴（limit=%d）", limit)
            return {"status": "skipped", "enhanced": 0, "degraded": 0}

        import asyncio

        enhanced = degraded = 0
        for post in rows:
            try:
                result = asyncio.run(enhance_experience_item(db, post))
            except Exception as e:  # noqa: BLE001
                logger.warning("[experience_enhance] 单条增强异常降级 %s: %s", post.id, e)
                result = {"status": "degraded"}
            if result.get("status") == "enhanced":
                enhanced += 1
            else:
                degraded += 1
            # 逐条提交：单条失败不回滚整批
            db.commit()

        logger.info("[experience_enhance] 批量完成 enhanced=%d degraded=%d", enhanced, degraded)
        return {"status": "success", "enhanced": enhanced, "degraded": degraded}
    except Exception as e:
        logger.error("[experience_enhance] 批量增强失败: %s", e)
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
