"""Skill 管理 API — 查询项目内置的 6 个专用 skill。"""
from fastapi import APIRouter, HTTPException

from app.skills.registry import list_skills, get_skill, get_skills_by_category

router = APIRouter(prefix="/api/skill-toolbox", tags=["skill-toolbox"])


@router.get("")
async def list_all_skills():
    """列出所有 skill。"""
    items = list_skills()
    return {"items": items, "total": len(items)}


@router.get("/{name}")
async def get_skill_detail(name: str):
    """获取指定 skill 的详细信息。"""
    skill = get_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return skill


@router.get("/category/{category}")
async def list_skills_by_category(category: str):
    """按分类列出 skill。"""
    items = get_skills_by_category(category)
    return {"items": items, "total": len(items), "category": category}
