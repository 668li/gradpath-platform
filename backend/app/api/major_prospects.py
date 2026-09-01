# backend/app/api/major_prospects.py
"""专业前景 API — 面向大一大二学生，按专业聚合真实就业/升学/考公数据。

数据全部带溯源（国家统计局 / 人社局工资价位 / 院校公开信息），纯规则聚合零 LLM。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import major_prospect_service as svc

router = APIRouter(prefix="/api/major-prospects", tags=["专业前景"])


class MajorListItem(BaseModel):
    name: str
    category: str
    source: str
    has_grad_intel: bool


class IndustrySalary(BaseModel):
    industry: str
    year: int
    salary_non_private: float
    salary_private: float | None
    vs_national: float
    source: str


class PositionSalary(BaseModel):
    position: str
    salary_median: int
    salary_min: int
    salary_max: int
    cities: list[str]
    source: str
    year: int


class CompanyItem(BaseModel):
    name: str
    industry: str
    size: str
    headquarters: str | None


class GradPathItem(BaseModel):
    school_name: str
    school_tier: str
    major_name: str
    year: int
    admission_ratio: str
    score_line: int | None
    push_ratio: str
    background_discrimination: str
    first_choice_protection: str


class CivilServiceInfo(BaseModel):
    level: str
    label: str
    note: str


class ProspectResponse(BaseModel):
    major: str
    matched_major: str
    exact_match: bool
    category: str
    industries: list[IndustrySalary]
    positions: list[PositionSalary]
    companies: list[CompanyItem]
    grad_paths: list[GradPathItem]
    civil_service: CivilServiceInfo
    related_majors: list[str]
    data_notes: list[str]


@router.get("/majors", response_model=list[MajorListItem])
def majors(db: Session = Depends(get_db)):
    """所有可选专业（映射表主干 + 已收录考研情报的专业）。"""
    return svc.list_majors(db)


@router.get("/detail", response_model=ProspectResponse)
def detail(
    major: str = Query(..., min_length=1, max_length=100, description="专业名称"),
    db: Session = Depends(get_db),
):
    """按专业聚合前景数据：行业薪资 / 岗位薪资 / 去向公司 / 考研路径 / 考公友好度。"""
    if not major.strip():
        raise HTTPException(status_code=422, detail="专业名称不能为空")
    return svc.get_prospect(db, major.strip())
