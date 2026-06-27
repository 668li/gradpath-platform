from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.dashboard_service import get_overview

router = APIRouter(prefix="/api/dashboard", tags=["个人看板"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_overview(db, user.id)
