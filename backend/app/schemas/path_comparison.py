"""多路径 What-If 对比 Schemas。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PathInput(BaseModel):
    """单条待对比路径输入。"""

    path_type: str = Field(..., description="路径类型，如 kaoyan/employment/civil_service")
    target_role: str = Field(
        ..., min_length=1, max_length=100, description="目标角色，如 '后端开发'"
    )


class EvidenceItem(BaseModel):
    """单条证据 — 每个数字的溯源（source_url 或来源说明）。"""

    label: str = Field(..., description="证据标题，如 '分数线 · 中山大学 2025'")
    value: str = Field(..., description="证据内容")
    source_url: str | None = Field(default=None, description="来源链接（无链接则为 None）")
    note: str | None = Field(default=None, description="补充说明（如无链接时的来源字段）")


class PathMetrics(BaseModel):
    """单条路径的量化指标。"""

    path_type: str = Field(..., description="路径类型")
    target_role: str = Field(..., description="目标角色")
    income_1y: str = Field(..., description="1 年预期收入区间，如 '10-15万'")
    income_3y: str = Field(..., description="3 年预期收入区间")
    income_5y: str = Field(..., description="5 年预期收入区间")
    risk_level: str = Field(..., description="风险等级：low / medium / high")
    risk_description: str = Field(..., description="风险说明")
    growth_score: int = Field(..., ge=1, le=10, description="成长性评分 1-10")
    time_cost_months: int = Field(..., ge=0, description="准备时间（月）")
    match_score: int = Field(..., ge=0, le=100, description="与用户画像匹配度 0-100")
    match_description: str = Field(..., description="匹配度说明")
    pros: list[str] = Field(default_factory=list, description="优势列表")
    cons: list[str] = Field(default_factory=list, description="劣势列表")
    # 决策引擎扩展：每条指标的溯源证据（老接口不传则为空，向后兼容）
    evidence: list[EvidenceItem] = Field(default_factory=list, description="证据溯源列表")

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        if v not in ("low", "medium", "high"):
            raise ValueError("risk_level must be one of: low, medium, high")
        return v


class ComparisonRequest(BaseModel):
    """对比请求体 — 2-3 条路径。"""

    paths: list[PathInput] = Field(..., description="待对比路径列表")

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: list[PathInput]) -> list[PathInput]:
        if len(v) < 2 or len(v) > 3:
            raise ValueError("paths must contain between 2 and 3 items")
        return v


class ComparisonResponse(BaseModel):
    """对比响应体。"""

    id: str = Field(..., description="对比记录 ID")
    metrics: list[PathMetrics] = Field(..., description="各路径的量化指标")
    recommendation: str = Field(..., description="综合建议（自然语言）")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class PathComparisonRecord(ComparisonResponse):
    """完整对比记录（含用户 ID），用于内部传递。"""

    user_id: UUID


# ----------------------------------------------------------------------
# 三路对比决策引擎 Schemas
# ----------------------------------------------------------------------
# 个人条件包的合法取值（决策飞轮可报边界过滤）
_FRESH_STATUSES = {"应届", "非应届"}
_PARTY_STATUSES = {"中共党员", "党员或团员", "群众"}
_EDUCATION_LEVELS = {"博士", "硕士", "本科", "大专"}
_GENDERS = {"男", "女"}

# 结果回传合法取值（仿 destination_decisions 的 status 语义）
_OUTCOME_STATUSES = {"pending", "following", "achieved", "abandoned"}
_SELECTED_PATHS = {"kaoyan", "civil_service", "employment"}


class DecisionEngineRequest(BaseModel):
    """三路对比请求体 — 用户学生档案 + 个人条件包。"""

    major: str = Field(..., min_length=1, max_length=100, description="专业关键词，如 '计算机'")
    region: str | None = Field(default=None, max_length=50, description="地区（省/市），如 '广东'")
    school_tier: str | None = Field(
        default=None, max_length=20, description="学校层次：985/211/双一流/普通"
    )
    graduation_year: int | None = Field(
        default=None, ge=2000, le=2100, description="毕业年份，默认 2026"
    )

    # === 决策飞轮：个人条件包（考公可报边界 + 竞争力分级）===
    fresh_status: str | None = Field(
        default=None, max_length=20, description="应届状态：应届 / 非应届"
    )
    party_status: str | None = Field(
        default=None, max_length=20, description="政治面貌：中共党员 / 党员或团员 / 群众"
    )
    education: str | None = Field(
        default=None, max_length=20, description="最高学历：博士 / 硕士 / 本科 / 大专"
    )
    has_grassroots: bool | None = Field(
        default=None, description="是否满足基层工作经历 / 服务基层项目要求"
    )
    gender: str | None = Field(default=None, max_length=10, description="性别：男 / 女")
    estimated_score: int | None = Field(
        default=None, ge=0, le=200, description="行测+申论预估总分（200 分制），用于个人竞争力分级"
    )

    @field_validator("fresh_status", "party_status", "education", "gender")
    @classmethod
    def _validate_personal_fields(cls, v: str | None, info) -> str | None:
        if v is None:
            return v
        allowed = {
            "fresh_status": _FRESH_STATUSES,
            "party_status": _PARTY_STATUSES,
            "education": _EDUCATION_LEVELS,
            "gender": _GENDERS,
        }[info.field_name]
        if v not in allowed:
            raise ValueError(f"{info.field_name} must be one of: {', '.join(sorted(allowed))}")
        return v


class TopPosition(BaseModel):
    """可报岗位示例 — 考公岗位级分析的展示单位。"""

    dept_name: str = Field(..., description="招录部门")
    position_name: str = Field(..., description="职位名称")
    work_location: str | None = Field(default=None, description="工作地点")
    recruit_count: int | None = Field(default=None, description="招录人数")
    min_score: float | None = Field(default=None, description="进面最低分（已公布）")
    score_label: str = Field(..., description="与个人预估分的对比标签（未估分则为分布说明）")
    source_url: str | None = Field(default=None, description="来源链接")


class PositionAnalysis(BaseModel):
    """考公岗位级分析 — 基于个人条件的可报清单 + 进面线分层。"""

    eligible_count: int = Field(..., description="可报国考岗位数（按职位去重）")
    province_count: int = Field(..., description="可报省考岗位数")
    score_band: str = Field(..., description="已公布进面线的可报岗位分数分布（P25-P75）")
    personalized_level: str | None = Field(
        default=None, description="个人竞争力分级：稳健 / 均衡 / 冲刺 / 未评估"
    )
    tier_summary: str | None = Field(default=None, description="分级岗位统计摘要")
    top_positions: list[TopPosition] = Field(default_factory=list, description="可报岗位示例")
    notes: list[str] = Field(default_factory=list, description="数据说明（如文本解析标注）")


class SchoolCompetitionItem(BaseModel):
    """考研院校级竞争力 — 命中院校的竞争档位 + 隐性情报。"""

    university_name: str
    major_name: str
    degree_type: str | None = Field(default=None, description="学硕 / 专硕")
    year: int | None = Field(default=None, description="年份")
    score_line: int | None = Field(default=None, description="复试线")
    ratio: str | None = Field(default=None, description="报录比（如 12.3:1）")
    competition: str = Field(..., description="竞争档位：偏高 / 中等 / 偏低")
    intel: str | None = Field(default=None, description="隐性情报（卡第一学历 / 保护一志愿等）")
    source_url: str | None = Field(default=None, description="来源链接")


class SchoolAnalysis(BaseModel):
    """考研院校级分析 — 现有覆盖范围内的院校竞争对比。"""

    matched_school_count: int = Field(..., description="命中院校数")
    coverage_note: str = Field(..., description="覆盖说明（如'当前覆盖 39 所院校'）")
    items: list[SchoolCompetitionItem] = Field(default_factory=list, description="院校竞争力明细")


class DecisionOutcomeSubmit(BaseModel):
    """结果回传请求体 — 用户记录「当时选了哪条路、结果如何」。"""

    selected_path: str = Field(..., description="所走路径：kaoyan / civil_service / employment")
    selected_label: str | None = Field(default=None, max_length=50, description="目标角色中文名")
    outcome_status: str = Field(
        ..., description="结果状态：pending / following / achieved / abandoned"
    )
    actual_outcome: str | None = Field(
        default=None, max_length=1000, description="实际结果描述（如'进面未上岸'）"
    )
    satisfaction: int | None = Field(default=None, ge=1, le=5, description="综合满意度 1-5")

    @field_validator("selected_path")
    @classmethod
    def _validate_selected_path(cls, v: str) -> str:
        if v not in _SELECTED_PATHS:
            raise ValueError(f"selected_path must be one of: {', '.join(sorted(_SELECTED_PATHS))}")
        return v

    @field_validator("outcome_status")
    @classmethod
    def _validate_outcome_status(cls, v: str) -> str:
        if v not in _OUTCOME_STATUSES:
            raise ValueError(
                f"outcome_status must be one of: {', '.join(sorted(_OUTCOME_STATUSES))}"
            )
        return v


class DecisionOutcomeInfo(BaseModel):
    """结果回传信息（响应内嵌）。"""

    selected_path: str | None = None
    selected_label: str | None = None
    outcome_status: str | None = None
    actual_outcome: str | None = None
    satisfaction: int | None = None
    reviewed_at: datetime | None = None


class DecisionEngineResponse(BaseModel):
    """三路对比响应体。"""

    id: str = Field(..., description="对比记录 ID")
    metrics: list[PathMetrics] = Field(..., description="三路量化指标（含证据溯源）")
    recommendation: str = Field(..., description="综合建议（自然语言）")
    input: dict = Field(default_factory=dict, description="实际使用的输入档案")
    created_at: datetime = Field(..., description="创建时间")

    # === 决策飞轮 ===
    position_analysis: PositionAnalysis | None = Field(
        default=None, description="考公岗位级分析（基于个人条件）"
    )
    school_analysis: SchoolAnalysis | None = Field(
        default=None, description="考研院校级分析（命中院校）"
    )
    outcome: DecisionOutcomeInfo | None = Field(
        default=None, description="结果回传信息（已记录时为非空）"
    )

    model_config = {"from_attributes": True}
