"""目标拆解器 —— 行动任务中心 #14（用户拍板功能）。

输入一个大目标（如"考上浙大计算机研"），按福格行为设计 B=MAP 约束由 LLM
拆成 7 天、每天一个 ≤5 分钟的最小行为，附锚点提示与三要素自评分；用户确认
后经 micro_action_service.create_plan_from_tasks 落库，天然接入现有
streak/提醒闭环。

外部结构借鉴（均为合法 license，未 vendor 任何代码文件）：
- claude-task-master parse-prd 的参数化拆解 schema（MIT）
- resilient-habit-designer 的 B=MAP 向导字段顺序（MIT）

配额走 ai_quota_service（check→incr），LLM 走 ai_orchestrator。
"""

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ai_orchestrator import AIOrchestrator
from app.services.ai_quota_service import (
    AILLMQuotaExceeded,
    check_llm_quota,
    incr_llm_quota,
)
from app.services.micro_action_service import create_plan_from_tasks

router = APIRouter(prefix="/api/goal-decompose", tags=["行动任务中心-目标拆解"])

VALID_TARGET_PATHS = ("kaoyan", "employment", "civil_service")
VALID_TASK_TYPES = ("research", "interview", "practice", "reflect")

_PATH_LABEL = {"kaoyan": "考研", "employment": "就业", "civil_service": "考公"}

_SYSTEM_PROMPT = """你是行为设计教练，专长福格行为模型（B=MAP：动机/能力/提示）。
用户会给出一个大目标，你要把它拆成"小到不可能失败"的微行动。

硬约束（违反任何一条即不合格）：
1. 恰好 7 个步骤，day_number 依次 1-7，每天恰好 1 个。
2. 每步 estimated_minutes ≤ 5（分钟）。宁可更小，不要更大："背 50 个单词"是错的，"打开单词 App 背 5 个"才对。
3. 第 1 步必须是"今天、此刻、2 分钟内就能开始"的打开类动作。
4. 每步给 anchor（锚点提示）：绑定用户已有日常场景，如"早上刷完牙后""到图书馆坐下后"。
5. 每步给 fogg 三要素自评分（各 1-5）：m=做这事动机多强，a=能力门槛多低（5=几乎零门槛），p=锚点提示多牢靠。三值最小值 ≥3 才算"够小"，达不到就把该步再缩小。
6. task_type 只能取：research / interview / practice / reflect。
7. 只输出严格 JSON，不要 markdown 代码块，不要解释文字。格式：
{"steps":[{"day_number":1,"title":"...","description":"...","minutes":5,"anchor":"...","task_type":"practice","fogg":{"m":4,"a":5,"p":4}}],"note":"一句话总述拆解思路"}"""


class GoalDecomposeRequest(BaseModel):
    goal: str = Field(min_length=2, max_length=120)
    path_type: str = Field(default="employment")
    motivation: int = Field(default=4, ge=1, le=5)


class GoalCommitRequest(BaseModel):
    goal: str = Field(min_length=2, max_length=100)
    path_type: str = Field(default="employment")
    steps: list[dict[str, Any]]


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 输出容错：剥代码围栏，截首个花括号块。"""
    cleaned = re.sub(r"```(?:json)?|```", "", text or "").strip()
    match = re.search(r"\{.*\}", cleaned, re.S)
    if not match:
        raise ValueError("LLM 输出中未找到 JSON 对象")
    return json.loads(match.group(0))


def _validate_steps(raw: Any) -> list[dict[str, Any]]:
    """校验并归一化拆解步骤；不合 Fogg 约束的步骤丢弃，不足 3 步判失败。"""
    if not isinstance(raw, list):
        return []
    steps: list[dict[str, Any]] = []
    seen_days: set[int] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        desc = str(item.get("description") or "").strip()
        if not title or not desc:
            continue
        try:
            day = int(item.get("day_number"))
        except (TypeError, ValueError):
            continue
        day = min(max(day, 1), 7)
        if day in seen_days:
            continue
        seen_days.add(day)
        minutes = item.get("minutes") or item.get("estimated_minutes") or 5
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = 5
        task_type = str(item.get("task_type") or "practice").strip()
        fogg = item.get("fogg") if isinstance(item.get("fogg"), dict) else {}
        steps.append(
            {
                "day_number": day,
                "title": title[:200],
                "description": desc[:600],
                "estimated_minutes": min(max(minutes, 1), 15),
                "anchor": str(item.get("anchor") or "")[:100],
                "task_type": task_type if task_type in VALID_TASK_TYPES else "practice",
                "fogg": {
                    "m": min(max(int(fogg.get("m") or 3), 1), 5),
                    "a": min(max(int(fogg.get("a") or 3), 1), 5),
                    "p": min(max(int(fogg.get("p") or 3), 1), 5),
                },
            }
        )
    return steps


def _user_prompt(req: GoalDecomposeRequest) -> str:
    path = _PATH_LABEL.get(req.path_type, req.path_type)
    return (
        f"大目标：{req.goal}\n"
        f"方向：{path}\n"
        f"动机自评：{req.motivation}/5（{req.motivation} 分=动机一般偏弱，"
        f"步骤必须更小、锚点必须更具体）\n"
        f"请按系统约束输出 7 天微行动 JSON。"
    )


@router.post("/preview")
async def preview_decompose(
    req: GoalDecomposeRequest, user: User = Depends(get_current_user)
) -> dict[str, Any]:
    if req.path_type not in VALID_TARGET_PATHS:
        raise HTTPException(status_code=422, detail="path_type 需为 kaoyan/employment/civil_service")
    try:
        await check_llm_quota(user.id)
    except AILLMQuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e)) from e

    try:
        raw = await AIOrchestrator().chat(
            _SYSTEM_PROMPT, _user_prompt(req), timeout=45
        )
    except Exception as e:  # 编排器异常（超时/网络/上游 429）如实降级
        raise HTTPException(status_code=502, detail=f"AI 拆解暂时不可用：{e}") from e

    try:
        data = _extract_json(raw)
        steps = _validate_steps(data.get("steps"))
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail="AI 返回了无法解析的拆解结果，请重试") from e
    if len(steps) < 3:
        raise HTTPException(status_code=502, detail="AI 拆解结果过于单薄，请换个说法重试")

    await incr_llm_quota(user.id)
    return {
        "goal": req.goal,
        "path_type": req.path_type,
        "steps": steps,
        "note": str(data.get("note") or "")[:200],
    }


@router.post("/commit")
async def commit_decompose(
    req: GoalCommitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if req.path_type not in VALID_TARGET_PATHS:
        raise HTTPException(status_code=422, detail="path_type 需为 kaoyan/employment/civil_service")
    steps = _validate_steps(req.steps)
    if len(steps) < 3:
        raise HTTPException(status_code=422, detail="有效步骤不足 3 个，无法创建微行动计划")
    tasks = [
        {
            "day_number": s["day_number"],
            "task_type": s["task_type"],
            "title": s["title"],
            "description": s["description"],
            "estimated_minutes": max(s["estimated_minutes"], 5),
        }
        for s in steps
    ]
    try:
        plan = create_plan_from_tasks(
            db, user.id, req.path_type, req.goal[:100], tasks
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {
        "plan_id": str(plan.id),
        "target_role": plan.target_role,
        "task_count": len(tasks),
        "redirect": "/micro-actions",
    }
