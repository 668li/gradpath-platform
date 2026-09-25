"""路径模拟器 API v2 — 真数据胜率推演（2026-09-25 重构）。

v1 的 10 年薪资/满意度/净资产预测已随"伪精确计算器"诊断判死，整文件重写。
业务逻辑全在 services/career_simulator_service.py（分布统计层）+
services/path_decision_engine.py（三线权威结论），本文件只做路由与校验。

presets/cities/industries 保留但内容适配新形态（路径类型/目标层次/系统簇）。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.career_simulator_service import simulate_paths

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/career-simulator", tags=["career"])

_VALID_PATH_TYPES = {"grad", "civil", "career"}
_VALID_TIERS = {"985", "211", "双一流", "普通"}
_VALID_CLUSTERS = {"police", "general", "central"}


class PathConfig(BaseModel):
    name: str = ""
    path_type: str  # grad | civil | career
    target: str | None = None  # grad: 985/211/双一流/普通；civil: police/general/central
    city: str | None = None
    estimated_score: int | None = None  # 考研估分(500制) / 考公模考分(200制)

    @field_validator("path_type")
    @classmethod
    def validate_path_type(cls, v: str) -> str:
        if v not in _VALID_PATH_TYPES:
            raise ValueError(f"path_type 必须是 {'/'.join(sorted(_VALID_PATH_TYPES))}")
        return v

    @field_validator("estimated_score")
    @classmethod
    def validate_score(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 500):
            raise ValueError("estimated_score 须在 0-500 之间（考研 500 制 / 考公 200 制）")
        return v


class SimulateRequest(BaseModel):
    paths: list[PathConfig]
    # 可选引擎输入：带 major 时叠加三路聚合引擎结论（劝退纪律/条件包/岗位级关联）
    major: str | None = None
    region: str | None = None
    school_tier: str | None = None
    graduation_year: int | None = None

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: list) -> list:
        if not 1 <= len(v) <= 3:
            raise ValueError("paths 须 1-3 条（对比超过 3 条反而看不清）")
        return v

    @field_validator("school_tier")
    @classmethod
    def validate_tier(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_TIERS:
            raise ValueError(f"school_tier 须是 {'/'.join(sorted(_VALID_TIERS))}")
        return v


@router.post("/simulate")
def simulate(req: SimulateRequest, db: Session = Depends(get_db)):
    """真数据胜率推演：分布指标 + 你的位置 + 证据链 + 诚实降级。无单点预测。"""
    try:
        engine_input = None
        if req.major:
            engine_input = {
                "major": req.major,
                "region": req.region,
                "school_tier": req.school_tier,
                "graduation_year": req.graduation_year,
                "estimated_score": next(
                    (p.estimated_score for p in req.paths if p.path_type == "civil"), None
                ),
                "kaoyan_estimated_score": next(
                    (p.estimated_score for p in req.paths if p.path_type == "grad"), None
                ),
            }
        return simulate_paths(
            db,
            [p.model_dump() for p in req.paths],
            engine_input=engine_input,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Career simulation failed: %s", e)
        raise HTTPException(status_code=500, detail="推演失败，请稍后重试")


@router.get("/presets")
def get_presets():
    """预设路径组合（适配新形态：路径类型+目标+说明）。"""
    return {
        "presets": [
            {
                "name": "考研 985",
                "path_type": "grad",
                "target": "985",
                "description": "目标 985 层次：报录比/复试线分布 + 你的位置",
            },
            {
                "name": "考研 211",
                "path_type": "grad",
                "target": "211",
                "description": "目标 211 层次：报录比/复试线分布 + 你的位置",
            },
            {
                "name": "考公·税务/统计系统",
                "path_type": "civil",
                "target": "general",
                "description": "综合口径系统进面线分布（200 分制模考分对照）",
            },
            {
                "name": "考公·公安/边检系统",
                "path_type": "civil",
                "target": "police",
                "description": "含专业科目口径簇（分数区间不同，分开统计）",
            },
            {
                "name": "直接就业",
                "path_type": "career",
                "description": "国家统计局官方薪资锚点（量级参照，不做个体预测）",
            },
        ]
    }


@router.get("/meta")
def get_meta():
    """枚举选项（层次/系统簇），供前端下拉。"""
    return {
        "tiers": [
            {"id": "985", "name": "985 层次"},
            {"id": "211", "name": "211 层次"},
        ],
        "clusters": [
            {"id": "general", "name": "税务/统计/海事等综合口径"},
            {"id": "police", "name": "公安/边检（含专业科目）"},
            {"id": "central", "name": "中央党群/部委"},
        ],
        "note": "双一流/普通层次当前样本不足（N<5），暂不提供分布参照",
    }
