"""AI 服务治理收口 API — 主线 b/F5（契约先行，方案 C）。

- GET  /api/admin/ai/governance-status → 真实动态检测：扫描 11 个 AI 服务，
  判定其源码是否统一接入 ``AIOrchestrator``，返回治理总览。
  （原 POST /api/ai/orchestrate 统一编排入口已下线 — 方案 C 决策，
  统一编排不落地，服务仍各自直连。）

检测口径：``importlib.import_module`` + ``inspect.getsource(module)`` 中
包含 ``AIOrchestrator`` 即视为已采纳。
"""
import importlib
import inspect
import logging

from fastapi import APIRouter

from app.schemas.ai_governance import GovernanceStatusVO, ServiceGovernanceVO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["AI服务治理"])

# 纳入治理的 11 个 AI 服务（主线 b/F5 治理清单）
_GOVERNED_SERVICES: tuple[str, ...] = (
    "decision_analysis_service",
    "decision_journal_service",
    "decision_advice_service",
    "mentor_persona_service",
    "life_wheel_service",
    "life_design_service",
    "growth_pattern_service",
    "growth_insight_service",
    "proactive_insight_service",
    "career_test_drive_service",
    "grad_intel_service",
)


def _detect_adoption(service_name: str) -> bool:
    """动态检测服务模块是否接入 AIOrchestrator（源码含其引用即判定采纳）。"""
    try:
        module = importlib.import_module(f"app.services.{service_name}")
        source = inspect.getsource(module)
        return "AIOrchestrator" in source
    except Exception as exc:  # noqa: BLE001 — 任一服务导入失败不应阻断治理总览
        logger.warning("治理检测失败 %s: %s", service_name, exc)
        return False


@router.get("/admin/ai/governance-status", response_model=GovernanceStatusVO)
def get_governance_status():
    """AI 服务治理总览（真实动态检测，非硬编码）。

    返回 11 个治理服务各自的采纳状态与总数，便于前端/运维核对收口进度。
    """
    services = [
        ServiceGovernanceVO(name=name, adopted=_detect_adoption(name))
        for name in _GOVERNED_SERVICES
    ]
    adopted = sum(1 for s in services if s.adopted)
    return GovernanceStatusVO(
        total=len(services),
        adopted=adopted,
        services=services,
    )
