"""010 T1 验收测试：life_design 的 LLM 调用前注入用户记忆（访谈原则引用纪律）。

验收对齐 010 spec §3：
- 正例：有 interview_principle_* 记忆 → system prompt 含事实内容 + 硬规则；
- 负例：无记忆新用户 → prompt 与现状完全一致（不出现背景块、不引用、不报错）；
- 健壮：上下文链路异常 → 降级为无注入，访谈照常。
"""

import asyncio
import uuid

import pytest

from app.models.user import User
from app.models.user_memory import MemoryFactType, UserMemoryFact
from app.services import life_design_service


class _CaptureOrchestrator:
    """捕获 system_prompt 的 AIOrchestrator 替身。"""

    captured: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, system_prompt=None, user_prompt=None, timeout=30, **kwargs):
        _CaptureOrchestrator.captured.append(system_prompt or "")
        return "AI 回复"


@pytest.fixture
def user(db_session):
    u = User(
        email=f"t1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        name="T1测试用户",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _add_principle(db_session, user) -> None:
    db_session.add(
        UserMemoryFact(
            user_id=user.id,
            fact_type=MemoryFactType.behavior,
            fact_key="interview_principle_1",
            fact_value="原则：先做一套真题再立假设；场景：考研决策；下回：先查目标院校近5年复试线",
            source="user_provided",
            confidence=90,
        )
    )
    db_session.commit()


def test_vision_injects_memory_and_rule(db_session, user, monkeypatch):
    _add_principle(db_session, user)
    _CaptureOrchestrator.captured = []
    monkeypatch.setattr(life_design_service, "AIOrchestrator", _CaptureOrchestrator)

    result = asyncio.run(
        life_design_service.generate_vision_from_audit(
            db_session, user.id, [{"question": "Q", "answer": "A"}]
        )
    )

    assert result == "AI 回复"
    assert _CaptureOrchestrator.captured, "LLM 应被调用"
    prompt = _CaptureOrchestrator.captured[0]
    assert "interview_principle_1" in prompt
    assert "先做一套真题再立假设" in prompt
    assert "不得编造记忆中没有的内容" in prompt


def test_no_memory_unchanged_behavior(db_session, user, monkeypatch):
    """负例：无记忆事实的新用户——无背景块、无硬规则，行为与现状一致。"""
    _CaptureOrchestrator.captured = []
    monkeypatch.setattr(life_design_service, "AIOrchestrator", _CaptureOrchestrator)

    result = asyncio.run(
        life_design_service.generate_vision_from_audit(
            db_session, user.id, [{"question": "Q", "answer": "A"}]
        )
    )

    assert result == "AI 回复"
    prompt = _CaptureOrchestrator.captured[0]
    assert "【此用户的已知背景】" not in prompt
    assert "不得编造记忆中没有的内容" not in prompt


def test_context_failure_degrades_gracefully(db_session, user, monkeypatch):
    """健壮：上下文链路异常 → 降级无注入，访谈照常出结果。"""
    _CaptureOrchestrator.captured = []

    def _boom(db, user_id):
        raise RuntimeError("context down")

    monkeypatch.setattr(life_design_service, "AIOrchestrator", _CaptureOrchestrator)
    monkeypatch.setattr(life_design_service, "build_context_prompt", _boom)

    result = asyncio.run(
        life_design_service.generate_vision_from_audit(
            db_session, user.id, [{"question": "Q", "answer": "A"}]
        )
    )

    assert result == "AI 回复"
    assert "【此用户的已知背景】" not in _CaptureOrchestrator.captured[0]
