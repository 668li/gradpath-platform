# backend/app/api/employment.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.employment_service import get_stats, list_majors, list_schools, search_employment

router = APIRouter(prefix="/api/employment", tags=["就业数据"])


@router.get("/search")
def search(
    school: str = Query(..., description="学校名称（模糊匹配）"),
    major: str = Query(..., description="专业名称（模糊匹配）"),
    year: int | None = Query(None, description="年份筛选"),
    degree: str | None = Query(None, description="学历筛选"),
    db: Session = Depends(get_db),
):
    return search_employment(db, school, major, year, degree)


@router.get("/schools")
def schools(db: Session = Depends(get_db)):
    return list_schools(db)


@router.get("/majors")
def majors(school: str = Query(...), db: Session = Depends(get_db)):
    return list_majors(db, school)


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
