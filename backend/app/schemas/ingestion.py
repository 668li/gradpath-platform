"""数据真实性接入层 Schema — 对齐系统设计 §3.2.M10.3 接口契约（方案 C：契约先行）。

字段严格对齐契约 DTO；枚举字段按契约以 str + 注释形式声明。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestTriggerRequest(BaseModel):
    """触发权威数据抓取请求（人工触发）。"""

    # ===== 必填字段 =====
    source_system: str = Field(
        ...,
        description="来源系统；枚举：yanzhao / school_official / manual",
    )
    biz_req_no: str = Field(..., max_length=64, description="业务请求号（幂等键，强制幂等）")
    # ===== 可选字段 =====
    url: str | None = Field(None, max_length=500, description="目标 URL（manual 录入时提供）")
    target_type: str | None = Field(None, description="目标类型；如 scoreline / program 等")


class IngestRunVO(BaseModel):
    """抓取运行状态 VO。

    run_id 为 str：映射 CrawlerRun.id（UUID），与 t_external_research_item.crawler_run_id
    同为字符串契约（存量 CrawlerRun.id 是 UUID，非 BIGINT）。
    """

    run_id: str = Field(..., description="抓取运行 ID（CrawlerRun.id，UUID 字符串）")
    source_system: str = Field(
        ..., description="来源系统；枚举：yanzhao / school_official / manual"
    )
    status: str = Field(..., description="运行状态；如 running / success / failed")
    total_items: int = Field(..., description="抓取总条数")
    pending_items: int = Field(..., description="待确认条数")
    created_time: datetime = Field(..., description="运行创建时间")


class IngestConfirmRequest(BaseModel):
    """人工确认字段入库请求（§3.2.M10.3，禁止自动入库）。"""

    # ===== 必填字段 =====
    run_id: str = Field(..., description="抓取运行 ID（CrawlerRun.id，UUID 字符串）")
    record_id: int = Field(..., description="待确认记录 ID（ExternalResearchItem.id）")
    operator_id: int = Field(..., description="运营审核员 ID")
    # ===== 业务字段 =====
    confirmed_fields: dict = Field(
        ...,
        description="人工确认后的字段（院校/专业/年份/复试线/报录比）",
    )
    source_url: str = Field(
        ..., max_length=500, description="公告原文链接（必填，来源追溯，合规红线 N1）"
    )
    source_system: str = Field(
        ...,
        description="来源系统；枚举：yanzhao / school_official / manual",
    )
    # ===== 可选字段 =====
    note: str | None = Field(None, max_length=500, description="备注")


class IngestRecordVO(BaseModel):
    """确认入库记录 VO。"""

    record_id: int = Field(..., description="记录 ID")
    run_id: str = Field(..., description="抓取运行 ID（CrawlerRun.id，UUID 字符串）")
    source_url: str = Field(..., description="来源链接")
    confirmed_fields: dict = Field(..., description="确认后的字段")
    status: str = Field(..., description="状态；如 approved / pending")
    created_time: datetime = Field(..., description="创建时间")


class DataSourceVO(BaseModel):
    """来源元数据 VO（§3.2.M10.3）。"""

    # ===== 基本信息 =====
    source_id: int = Field(..., description="来源元数据 ID")
    # ===== 业务字段 =====
    source_system: str = Field(..., description="来源系统枚举")
    source_url: str = Field(..., description="来源链接（唯一索引）")
    crawled_at: datetime = Field(..., description="采集时间")
    credibility: str = Field(
        ...,
        description="三级可信度；枚举：official_verified / user_reported / model_inferred",
    )
    verify_count: int = Field(..., description="验证次数")
    reviewed_by: str | None = Field(None, max_length=64, description="审核人")
    # ===== 状态字段 =====
    review_status: str = Field(..., description="枚举：PENDING / APPROVED / REJECTED")
    # ===== 时间字段 =====
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class SourceListVO(BaseModel):
    """来源与可信度配置列表 VO。"""

    items: list[DataSourceVO] = Field(..., description="来源列表")
    total: int = Field(..., description="总数")


class SourceUpdateRequest(BaseModel):
    """更新来源可信度配置请求（部分更新，均可选）。"""

    credibility: str | None = Field(
        None,
        description="三级可信度；枚举：official_verified / user_reported / model_inferred",
    )
    review_status: str | None = Field(None, description="枚举：PENDING / APPROVED / REJECTED")
    verify_count: int | None = Field(None, ge=0, description="验证次数")
