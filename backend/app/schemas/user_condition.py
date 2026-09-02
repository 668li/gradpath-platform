"""报考条件账本 Pydantic schemas"""

from pydantic import BaseModel, Field


class ConditionItem(BaseModel):
    """一条报考条件 — 由 gwy_position 行规则生成。"""

    key: str = Field(..., description="条件键，如 education / major / cert_0")
    label: str = Field(..., description="条件名称，如 学历要求")
    required: str = Field(..., description="职位表原文要求")
    source_field: str = Field(..., description="溯源：来自职位表的哪个字段")
    # 条件类型 — 决定「未满足」时该关注什么：
    #   hard_gate  资格硬门槛（学位/政治面貌/基层年限等锁死项，不满足基本无望）
    #   actionable 可补项（证书/考试/分数等，努力可获得，不影响"能不能报"）
    #   unclassified 无法可靠判定类型（措辞开放），不武断
    category: str = Field("unclassified", description="hard_gate / actionable / unclassified")


class ConditionProgress(BaseModel):
    """条件完成度 — 北极星指标「条件完成率」的职位级视图。"""

    total: int
    met: int
    in_progress: int
    unmet: int
    rate: float = Field(..., description="完成率百分比 0-100")


class ConditionChecklistResponse(BaseModel):
    """目标职位条件清单 + 用户核对状态 + 完成度。"""

    position_id: str
    position_code: str
    position_name: str | None = None
    dept_name: str | None = None
    year: int
    exam_source: str = Field("national", description="national=国考 / province=省考")
    conditions: list[ConditionItem]
    statuses: dict[str, str] = Field(..., description="条件键 → unmet/in_progress/met")
    progress: ConditionProgress


class ConditionStatusUpdateRequest(BaseModel):
    """勾选一条条件的完成状态。"""

    position_id: str = Field(..., min_length=32, max_length=32)
    exam_source: str = Field("national", pattern="^(national|province|kaoyan)$")
    condition_key: str = Field(..., min_length=1, max_length=50)
    status: str = Field(..., pattern="^(unmet|in_progress|met)$")


class ConditionPreviewRequest(BaseModel):
    """免费可报性预览 — 免登录勾选身份字段，立即判定能否报考。

    与登录后条件账本共用同一套可报性判定（path_decision_engine.blockers），
    只是无需用户身份：访客手动填的字段即身份快照。
    """

    exam_source: str = Field("national", pattern="^(national|province|kaoyan)$")
    position_ref: str = Field(
        ..., min_length=1, max_length=100, description="职位主键；考研传专业 UUID"
    )
    fresh_status: str | None = Field(None, description="应届/非应届")
    party_status: str | None = Field(None, description="中共党员/党员或团员/群众")
    education: str | None = Field(None, description="博士/硕士/本科/大专")
    has_grassroots: bool | None = Field(None, description="是否已满足基层工作经历")
    gender: str | None = Field(None, description="男/女")
    estimated_score: int | None = Field(None, ge=0, le=300, description="国考/省考总分估分")
    kaoyan_estimated_score: int | None = Field(None, ge=0, le=500, description="考研初试估分")


class ConditionBlockItem(BaseModel):
    """一条被挡住的资格维度 — 免费预览结果卡逐条展示。"""

    key: str
    label: str
    reason: str


class ConditionPreviewResponse(BaseModel):
    """免费可报性预览判定结果。

    national/province：eligible + blockers + verdict_text；
    kaoyan：level + total_score_line + score_lines + verdict_text（eligible 恒为 None）。
    """

    exam_source: str
    position_ref: str
    position_name: str | None = None
    dept_name: str | None = None
    eligible: bool | None = None
    blockers: list[ConditionBlockItem] = Field(default_factory=list)
    verdict_text: str | None = None
    # 未填维度的可报性提示（仅 national/province）：判定基于不完整身份，标注哪些字段没填
    missing_fields: list[str] = Field(
        default_factory=list,
        description="访客未填写的身份维度（fresh_status/party_status/education/has_grassroots/gender）",
    )
    has_missing: bool = Field(default=False, description="是否存在未填写的身份维度")
    # kaoyan 专用
    university_name: str | None = None
    major_name: str | None = None
    level: str | None = None
    total_score_line: float | None = None
    score_lines: dict[str, float] | None = Field(
        None, description="单科线：politics / foreign_language / business_1 / business_2"
    )
