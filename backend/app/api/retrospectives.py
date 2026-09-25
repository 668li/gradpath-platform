import logging
from datetime import date
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.retrospective import (
    ActionReviewRequest,
    ActionsCreateRequest,
    AIRetroDraftRequest,
    AIRetroDraftResponse,
    PrincipleCreate,
    PrincipleDraftRequest,
    PrincipleUpdate,
    PrincipleVerifyRequest,
    ReflectRequest,
    RetroCreate,
    RetroResponse,
    RetroUpdate,
)
from app.services.ai_service import AIServiceNotConfigured
from app.services.retro_ai_service import (
    draft_principles,
    generate_ai_retro_draft,
    guide_reflection,
)
from app.services.retro_principle_service import (
    action_to_dict,
    build_replay,
    create_actions,
    create_principle,
    deactivate_principle,
    ensure_example_principles,
    list_due_actions,
    list_principles,
    principle_to_dict,
    review_action,
    update_principle,
    verify_principle,
)
from app.services.retrospective_service import (
    create_retrospective,
    delete_retrospective,
    generate_draft,
    get_retrospective,
    list_retrospectives_paginated,
    update_retrospective,
)
from app.services.weekly_draft_service import generate_weekly_draft

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retrospectives", tags=["阶段复盘"])


@router.post("", response_model=RetroResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: RetroCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return create_retrospective(db, user.id, data)


@router.get("", response_model=PaginatedResponse[RetroResponse])
def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = list_retrospectives_paginated(db, user.id, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/draft")
def draft(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return generate_draft(db, user.id, period_start, period_end)


@router.get("/weekly-draft")
def weekly_draft(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 周报草稿：基于本周行为数据自动生成4层模板。

    4层：数据层→对比层→洞察层→行动层。
    纯 DB 聚合，不依赖 LLM，零成本生成。
    """
    return generate_weekly_draft(db, user.id)


@router.post("/ai-draft", response_model=AIRetroDraftResponse)
@limiter.limit(rate_limits.RETROSPECTIVE_AI_DRAFT)
async def ai_draft(
    request: Request,
    response: Response,
    body: AIRetroDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 复盘草稿 — 需登录。

    基于用户指定时段内的职业事件（含 STAR 细节）调用 LLM 生成结构化复盘草稿。
    不持久化，由前端决定是否保存为正式复盘。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 → 504
    - 其他异常 → 500
    """
    try:
        return await generate_ai_retro_draft(db, user.id, body.period_start, body.period_end)
    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置（LLM_API_KEY 缺失）",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("AI 复盘草稿服务异常: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 复盘草稿服务异常，请稍后重试",
        )


# ======================================================================
# 复盘深化（2026-09-25）：事实回放 / 原则库 / Try 行动卡 / AI 引导反思
# 路由顺序：静态段路由必须先于 /{retro_id} 注册，否则 /principles 会被
# UUID 路径参数拦截成 422（FastAPI 按注册顺序匹配）。
# ======================================================================


@router.get("/replay")
def replay(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """事实回放：四源聚合（节点回传/职业事件/条件缺口/到期行动卡）。纯 DB 零 LLM。"""
    if period_end < period_start:
        raise HTTPException(status_code=422, detail="period_end 不能早于 period_start")
    return build_replay(db, user.id, period_start, period_end)


@router.get("/principles")
def list_principles_endpoint(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """原则库列表（首次访问自动预置示例破冷启动）。"""
    ensure_example_principles(db, user.id)
    return {"principles": list_principles(db, user.id)}


@router.post("/principles", status_code=status.HTTP_201_CREATED)
def create_principle_endpoint(
    data: PrincipleCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """创建原则（空话闸拦截"要更努力"式空洞条目）。"""
    p, err = create_principle(
        db,
        user.id,
        data.trigger_scene,
        data.action,
        data.rationale,
        data.scene_tags,
        data.source_retro_id,
    )
    if err:
        raise HTTPException(status_code=422, detail=err)
    return principle_to_dict(p)


@router.patch("/principles/{principle_id}")
def update_principle_endpoint(
    principle_id: UUID,
    data: PrincipleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修订原则（修订后回 draft 态重走验证——原则是活的）。"""
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    p, err = update_principle(db, user.id, principle_id, **fields)
    if err:
        raise HTTPException(status_code=422, detail=err)
    if not p:
        raise HTTPException(status_code=404, detail="原则不存在")
    return principle_to_dict(p)


@router.post("/principles/{principle_id}/verify")
def verify_principle_endpoint(
    principle_id: UUID,
    data: PrincipleVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """原则复审裁决：again（再次有效，verify_count+1）/ ineffective（失效）/ pending（顺延）。"""
    p, err = verify_principle(db, user.id, principle_id, data.verdict, data.note)
    if err:
        raise HTTPException(status_code=422, detail=err)
    if not p:
        raise HTTPException(status_code=404, detail="原则不存在")
    return principle_to_dict(p)


@router.delete("/principles/{principle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_principle_endpoint(
    principle_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if not deactivate_principle(db, user.id, principle_id):
        raise HTTPException(status_code=404, detail="原则不存在")


@router.post("/actions", status_code=status.HTTP_201_CREATED)
def create_actions_endpoint(
    data: ActionsCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """为复盘创建 Try 行动卡（≤3 条，带触发场景与复审日期）。"""
    cards, err = create_actions(db, user.id, data.retro_id, [i.model_dump() for i in data.items])
    if err:
        raise HTTPException(status_code=422, detail=err)
    return {"actions": [action_to_dict(c) for c in cards]}


@router.get("/actions/due")
def due_actions_endpoint(
    include_future_days: int = Query(0, ge=0, le=14),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """到期待复审的行动卡（新建复盘开场先复审——KPT Try 复审闭环）。"""
    return {"actions": list_due_actions(db, user.id, include_future_days)}


@router.post("/actions/{action_id}/review")
def review_action_endpoint(
    action_id: UUID,
    data: ActionReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """行动卡复审裁决。effective 会自动升级为已验证原则（闭环）。"""
    action, principle, err = review_action(db, user.id, action_id, data.verdict, data.note)
    if err:
        raise HTTPException(status_code=422, detail=err)
    if not action:
        raise HTTPException(status_code=404, detail="行动卡不存在")
    return {
        "action": action_to_dict(action),
        "upgraded_principle": principle_to_dict(principle) if principle else None,
    }


@router.post("/reflect")
@limiter.limit(rate_limits.RETROSPECTIVE_AI_DRAFT)
async def reflect_endpoint(
    request: Request,
    body: ReflectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 教练引导反思：一次一问、先情绪后归因、双我思维。降级策略同 ai-draft。"""
    context_summary = None
    if body.period_start and body.period_end:
        try:
            replay = build_replay(db, user.id, body.period_start, body.period_end)
            parts = []
            if replay["node_feedbacks"]:
                parts.append(
                    "节点回传："
                    + "；".join(
                        f"{n['node_title']}({n['status']})" for n in replay["node_feedbacks"][:10]
                    )
                )
            if replay["career_events"]:
                parts.append(
                    "职业事件："
                    + "；".join(
                        f"{e['event_date']}[{e['event_type']}]{e['title']}"
                        for e in replay["career_events"][:10]
                    )
                )
            if replay["condition_summary"]:
                cs = replay["condition_summary"]
                parts.append(
                    f"条件缺口：目标{cs.get('position_name', '')} 条件完成 {cs.get('met', 0)}/{cs.get('total', 0)}"
                )
            context_summary = "\n".join(parts) or None
        except Exception:
            logger.exception("reflect 上下文聚合失败，降级为无上下文")
    try:
        return await guide_reflection(body.messages, context_summary)
    except AIServiceNotConfigured:
        raise HTTPException(status_code=503, detail="AI 服务未配置（LLM_API_KEY 缺失）")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 引导超时，请稍后重试")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("AI 引导反思异常: %s", e)
        raise HTTPException(status_code=500, detail="AI 引导反思服务异常，请稍后重试")


@router.post("/principle-draft")
@limiter.limit(rate_limits.RETROSPECTIVE_AI_DRAFT)
async def principle_draft_endpoint(
    request: Request,
    body: PrincipleDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从复盘内容提炼 if-then 原则草稿（≤3 条，空话闸双保险）。"""
    try:
        items = await draft_principles(body.retro_content)
        return {"principles": items}
    except AIServiceNotConfigured:
        raise HTTPException(status_code=503, detail="AI 服务未配置（LLM_API_KEY 缺失）")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 提炼超时，请稍后重试")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("AI 原则提炼异常: %s", e)
        raise HTTPException(status_code=500, detail="AI 原则提炼服务异常，请稍后重试")


# ======================================================================
# /{retro_id} 动态段路由（注册顺序在所有静态段之后——FastAPI 按注册顺序匹配）
# ======================================================================


@router.get("/{retro_id}", response_model=RetroResponse)
def get_one(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_retrospective(db, user.id, retro_id)


@router.patch("/{retro_id}", response_model=RetroResponse)
def update(
    retro_id: UUID,
    data: RetroUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return update_retrospective(db, user.id, retro_id, data)


@router.delete("/{retro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_retrospective(db, user.id, retro_id)
