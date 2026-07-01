from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_refresh_token
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import login, register

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def register_endpoint(
    request: Request,
    response: Response,
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    return register(db, data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_endpoint(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    return login(db, data.email, data.password)


@router.get("/me", response_model=UserResponse)
def me_endpoint(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(body: RefreshRequest):
    """用 refresh_token 换取新的 access_token。"""
    user_id = verify_refresh_token(body.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="refresh_token 无效或已过期")
    new_access_token = create_access_token(str(user_id))
    return RefreshResponse(access_token=new_access_token)
