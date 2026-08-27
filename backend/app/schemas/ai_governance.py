"""AI 服务治理 Schema — 对齐主线 b/F5「AI 治理收口」接口契约（方案 C：契约先行）。

治理面：
- GET /api/admin/ai/governance-status → GovernanceStatusVO

（原 POST /api/ai/orchestrate 统一编排入口已下线 — 方案 C 决策，
OrchestrateRequest/OrchestrateVO 随之下线。）
"""

from pydantic import BaseModel, Field


class ServiceGovernanceVO(BaseModel):
    """单个 AI 服务的治理状态。"""

    name: str = Field(..., description="服务模块名（如 career_test_drive_service）")
    adopted: bool = Field(..., description="是否已统一接入 AIOrchestrator")


class GovernanceStatusVO(BaseModel):
    """AI 服务治理总览。"""

    total: int = Field(..., description="纳入治理的 AI 服务总数")
    adopted: int = Field(..., description="已接入 AIOrchestrator 的服务数")
    services: list[ServiceGovernanceVO] = Field(..., description="各服务治理明细")
