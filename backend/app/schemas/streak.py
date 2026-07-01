from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int
    today_active: bool
    last_active_date: date | None
    freeze_available: bool
    recent_records: list[dict]

    model_config = {"from_attributes": True}


class StreakCheckInResponse(BaseModel):
    streak_count: int
    activity_types: list[str]
    xp_earned: int
    is_new_record: bool
