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
