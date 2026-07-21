from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class StreakMilestone(BaseModel):
    days: int
    name: str
    unlocked: bool


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int
    today_active: bool
    last_active_date: date | None
    freeze_available: bool
    recent_records: list[dict]
    milestones: list[StreakMilestone] = []
    rest_day_available: bool = True
    redeem_available: bool = False

    model_config = {"from_attributes": True}


class StreakCheckInResponse(BaseModel):
    streak_count: int
    activity_types: list[str]
    xp_earned: int
    is_new_record: bool


class StreakCheckInRequest(BaseModel):
    action_type: str = "main"  # "main" | "micro"
    action_detail: str = ""


class StreakRestDayResponse(BaseModel):
    streak_count: int
    message: str


class StreakRedeemResponse(BaseModel):
    streak_count: int
    message: str
    redeemed: bool
