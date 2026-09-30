"""路径模拟器 API v2 — 已退役（2026-09-26 拍板）。

前端整站隐藏、入口摘除后，后端端点收敛为：
- POST /simulate：鉴权 + 一律 410 Gone（防退役功能被匿名滥用）
- GET /presets、/meta：静态枚举保留（退役说明页与历史客户端仍可读）

业务逻辑仍在 services/career_simulator_service.py（分布统计层）+
services/path_decision_engine.py（三线权威结论），本文件只做路由。
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/career-simulator", tags=["career"])


@router.post("/simulate")
def simulate(_user: User = Depends(get_current_user)):
    """路径模拟器已退役（2026-09-26 拍板整站隐藏）。

    端点不再执行推演：鉴权后一律 410 Gone，防止退役功能被匿名滥用。
    """
    raise HTTPException(
        status_code=410,
        detail="路径模拟器已退役，请使用决策引擎（/api/path-decision/analyze）获取路径对比结论",
    )


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
