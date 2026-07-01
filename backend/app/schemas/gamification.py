# backend/app/schemas/gamification.py
"""游戏化相关 Pydantic 模型。"""
from pydantic import BaseModel


class BadgeInfo(BaseModel):
    code: str
    name: str
    description: str
    icon: str


class ProgressInfo(BaseModel):
    current: int
    needed: int
    percent: int


class GamificationProfileResponse(BaseModel):
    xp: int
    level: int
    level_name: str
    progress: ProgressInfo
    earned_badges: list[BadgeInfo]
    available_badges: list[BadgeInfo]
    newly_awarded: list[BadgeInfo]


class UserSettingResponse(BaseModel):
    share_skills_enabled: bool
    share_token: str | None


class UserSettingUpdate(BaseModel):
    share_skills_enabled: bool
