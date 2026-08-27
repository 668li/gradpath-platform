"""家庭对话脚手架 Schemas。"""

from datetime import datetime

from pydantic import BaseModel, Field

# 支持的父母类型
PARENT_ARCHETYPES = (
    "stability_first",  # 考公稳定，不用担心失业
    "prestige_first",  # 公务员有面子，说出去好听
    "practical_worry",  # 现在经济不好，先求稳
    "supportive",  # 你自己决定，但要考虑清楚
)


class FamilyDialogueStart(BaseModel):
    """启动家庭对话脚手架的请求体。"""

    parent_concern: str = Field(
        ..., min_length=1, max_length=200, description="父母主要担心什么，如「爸妈想让我考公」"
    )
    user_choice: str = Field(
        ..., min_length=1, max_length=200, description="用户想选什么，如「我想去互联网公司」"
    )
    parent_archetype: str = Field(
        ..., description="父母类型: stability_first/prestige_first/practical_worry/supportive"
    )


class Argument(BaseModel):
    """单条论据 — 把父母的话术翻译成数据化回应 + 共情提示。"""

    parent_saying: str = Field(..., description="父母可能说的话")
    user_response: str = Field(..., description="建议回应")
    data_backing: str = Field(..., description="数据支撑")
    empathy_note: str = Field(..., description="共情提示")


class FamilyDialogueResponse(BaseModel):
    """家庭对话脚手架响应 — 含理解分析、论据、沟通技巧。"""

    id: str
    parent_concern: str
    user_choice: str
    parent_archetype: str | None = None
    understanding: str = Field("", description="理解父母担忧的分析")
    arguments: list[Argument] = Field(default_factory=list, description="准备的论据")
    talking_tips: list[str] = Field(default_factory=list, description="沟通技巧")
    practice_messages: list[dict] = Field(default_factory=list, description="模拟对话记录")
    status: str = "preparing"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PracticeMessage(BaseModel):
    """单条模拟对话消息。"""

    role: str = Field(..., description="parent/user")
    content: str = Field(..., description="消息内容")


class PracticeRequest(BaseModel):
    """模拟对话练习请求体。"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户输入要说的话")
