"""Evidence Provider Router（D9 Phase 2.1）——白名单内部库 → 候选证据。

纪律（CONTEXT.md + 拍板 Q8）：
- Provider 只产候选证据：不落库、不验证；用户点选后才走既有 POST evidence
  入账（创建一律 internal_unverified，闸在 evidence 服务层）。
- 白名单硬闸：provider 名不在表内=404，绝不随机路由；未知/他人 hypothesis=404。
- 只接有溯源的库（grad_intel/civil_service_intel/experience_post/employment_data/
  market_data）；school/company 无 source 字段（Q8 拍板延后），DarkKnowledge 为
  0 行只读底座不接。
- 可见性：grad 情报/分数线/招简为共享橱窗库全量可见（仅滤 AI 生成行）；
  civil_post/experience_post 按各自语义过滤；AI 生成行不出候选（零造假红线）。
"""

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.civil_service_intel import PostIntel
from app.models.employment_data import EmploymentData
from app.models.experience_post import ExperiencePost
from app.models.grad_intel import GradSchoolIntel, GradScorelineRecord, GradYanzhaoProgram
from app.models.market_data import MarketData
from app.services.decision_os_service import get_hypothesis

logger = logging.getLogger(__name__)

_MAX_CANDIDATES = 5


def _first_url(value) -> str | None:
    """从溯源字段（JSONB 列表 / 字符串 / dict）取第一个 http(s) URL。"""
    if not value:
        return None
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, dict):
            item = item.get("url") or item.get("source") or ""
        text = str(item).strip()
        if text.startswith("http://") or text.startswith("https://"):
            return text
    return None


def _unknown_bits(mapping: dict[str, str | None]) -> list[str]:
    return [f"{k}={v}" for k, v in mapping.items() if v and v not in ("unknown", "")]


def _search_grad_school_intel(db: Session, user_id: UUID, query: str) -> list[dict]:
    # 情报库是共享橱窗（user_id 非空但语义为策展来源，非隐私），全量可见；
    # 只滤 AI 生成行（零造假红线）。
    rows = (
        db.query(GradSchoolIntel)
        .filter(
            GradSchoolIntel.is_ai_generated.is_(False),
            or_(
                GradSchoolIntel.school_name.ilike(f"%{query}%"),
                GradSchoolIntel.major_name.ilike(f"%{query}%"),
            ),
        )
        .order_by(GradSchoolIntel.year.desc())
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        bits = [f"{r.school_name} {r.major_name}（{r.year} 年）"]
        bits += _unknown_bits(
            {
                "背景歧视": r.background_discrimination,
                "一志愿保护": r.first_choice_protection,
                "压分": r.score_suppression,
                "复试权重": r.retest_weight,
                "推免占比": r.push_ratio,
                "报录比": r.admission_ratio,
            }
        )
        if r.insider_notes:
            bits.append(f"内情：{r.insider_notes[:80]}")
        out.append(
            {
                "claim": "；".join(bits),
                "source": "GradPath 院校情报库（策展）",
                "source_url": _first_url(r.data_sources),
                "source_type": "internal_db",
                "reliability": "medium",
                "provider": "internal:grad_school_intel",
                "observed_on": None,
            }
        )
    return out


def _search_grad_scoreline(db: Session, user_id: UUID, query: str) -> list[dict]:
    rows = (
        db.query(GradScorelineRecord)
        .filter(
            or_(
                GradScorelineRecord.university_name.ilike(f"%{query}%"),
                GradScorelineRecord.major_name.ilike(f"%{query}%"),
            )
        )
        .order_by(GradScorelineRecord.year.desc())
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        bits = [f"{r.university_name} {r.major_name}（{r.year}）总分线 {r.total_score_line or '无'}"]
        singles = {
            "政": r.politics_score,
            "外": r.foreign_language_score,
            "业一": r.business_1_score,
            "业二": r.business_2_score,
        }
        if any(v is not None for v in singles.values()):
            bits.append("单科 " + " ".join(f"{k}{v}" for k, v in singles.items() if v is not None))
        if r.application_count and r.enrollment_count:
            bits.append(f"报录 {r.application_count}/{r.enrollment_count}")
        out.append(
            {
                "claim": "，".join(bits),
                "source": "GradPath 分数线库",
                "source_url": _first_url(r.data_sources),
                "source_type": "internal_db",
                "reliability": "high",
                "provider": "internal:grad_scoreline",
                "observed_on": None,
            }
        )
    return out


def _search_grad_yanzhao(db: Session, user_id: UUID, query: str) -> list[dict]:
    rows = (
        db.query(GradYanzhaoProgram)
        .filter(
            or_(
                GradYanzhaoProgram.university_name.ilike(f"%{query}%"),
                GradYanzhaoProgram.major_name.ilike(f"%{query}%"),
            )
        )
        .order_by(GradYanzhaoProgram.year.desc())
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        bits = [f"{r.university_name}{r.department} {r.major_name}（{r.year} 招简）"]
        if r.enrollment_quota:
            bits.append(f"拟招 {r.enrollment_quota}")
        if r.duration:
            bits.append(f"学制 {r.duration}")
        if r.admission_requirements:
            bits.append(f"要求：{r.admission_requirements[:100]}")
        out.append(
            {
                "claim": "；".join(bits),
                "source": "GradPath 招简库",
                "source_url": r.source_url or _first_url(r.data_sources),
                "source_type": "internal_db",
                "reliability": "high",
                "provider": "internal:grad_yanzhao",
                "observed_on": None,
            }
        )
    return out


def _search_civil_post(db: Session, user_id: UUID, query: str) -> list[dict]:
    rows = (
        db.query(PostIntel)
        .filter(
            PostIntel.user_id == str(user_id),
            or_(
                PostIntel.region.ilike(f"%{query}%"),
                PostIntel.department.ilike(f"%{query}%"),
                PostIntel.post_name.ilike(f"%{query}%"),
            ),
        )
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        bits = [f"{r.region} {r.department} {r.post_name}"]
        bits += _unknown_bits(
            {
                "真实竞争度": r.real_competition,
                "待遇": r.treatment_level,
                "萝卜岗": r.radish_post,
                "服务期": r.service_period,
                "晋升": r.promotion_speed,
            }
        )
        if r.admission_ratio:
            bits.append(f"报录比 {r.admission_ratio}")
        out.append(
            {
                "claim": "；".join(bits),
                "source": "GradPath 考公情报库",
                "source_url": _first_url(r.data_sources),
                "source_type": "internal_db",
                "reliability": "medium",
                "provider": "internal:civil_post",
                "observed_on": None,
            }
        )
    return out


def _search_experience_post(db: Session, user_id: UUID, query: str) -> list[dict]:
    rows = (
        db.query(ExperiencePost)
        .filter(
            ExperiencePost.status == "approved",
            or_(
                ExperiencePost.title.ilike(f"%{query}%"),
                ExperiencePost.content.ilike(f"%{query}%"),
            ),
        )
        .order_by(ExperiencePost.like_count.desc())
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        summary = r.summary or (r.content or "")[:150]
        reliability = (
            "medium" if (r.is_verified or (r.quality_grade or "") in ("A", "B")) else "low"
        )
        out.append(
            {
                "claim": f"经验贴《{r.title}》：{summary}",
                "source": f"{r.source_platform or 'user'} 经验贴",
                "source_url": r.source_url,
                "source_type": "peer",
                "reliability": reliability,
                "provider": "internal:experience_post",
                "observed_on": None,
            }
        )
    return out


def _search_employment(db: Session, user_id: UUID, query: str) -> list[dict]:
    rows = (
        db.query(EmploymentData)
        .filter(EmploymentData.major.ilike(f"%{query}%"))
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        bits = [f"{r.major}（{r.degree.value if hasattr(r.degree, 'value') else r.degree}）"]
        if r.employment_rate is not None:
            bits.append(f"就业率 {r.employment_rate:.1%}")
        if r.further_study_rate is not None:
            bits.append(f"升学 {r.further_study_rate:.1%}")
        if r.civil_service_rate is not None:
            bits.append(f"考公 {r.civil_service_rate:.1%}")
        out.append(
            {
                "claim": "，".join(bits),
                "source": "GradPath 就业数据库",
                "source_url": r.source_url,
                "source_type": "internal_db",
                "reliability": "medium",
                "provider": "internal:employment",
                "observed_on": None,
            }
        )
    return out


def _search_market(db: Session, user_id: UUID, query: str) -> list[dict]:
    rows = (
        db.query(MarketData)
        .filter(
            or_(
                MarketData.indicator.ilike(f"%{query}%"),
                MarketData.industry.ilike(f"%{query}%"),
            )
        )
        .order_by(MarketData.year.desc())
        .limit(_MAX_CANDIDATES)
        .all()
    )
    out = []
    for r in rows:
        scope = r.region or r.industry or "全国"
        out.append(
            {
                "claim": f"{r.indicator}（{scope}，{r.year}）= {r.value}{r.unit}",
                "source": r.source,
                "source_url": r.source_url,
                "source_type": "internal_db",
                "reliability": "medium",
                "provider": "internal:market",
                "observed_on": None,
            }
        )
    return out


# 白名单：名字 → (展示名, 检索函数)。检索函数签名 (db, user_id, query)。
_PROVIDERS: dict[str, tuple[str, Callable[[Session, UUID, str], list[dict]]]] = {
    "grad_school_intel": ("院校情报", _search_grad_school_intel),
    "grad_scoreline": ("分数线", _search_grad_scoreline),
    "grad_yanzhao": ("招简", _search_grad_yanzhao),
    "civil_post": ("考公职位情报", _search_civil_post),
    "experience_post": ("经验贴", _search_experience_post),
    "employment": ("就业数据", _search_employment),
    "market": ("市场数据", _search_market),
}


def list_providers() -> list[dict]:
    """白名单清单（前端渲染 Provider 面板用）。"""
    return [{"name": name, "label": label} for name, (label, _) in _PROVIDERS.items()]


def search_provider(
    db: Session, user_id: UUID, hypothesis_id: UUID, provider_name: str, query: str
) -> list[dict]:
    """按白名单 Provider 检索候选证据。

    未知 provider / 未知或他人 hypothesis 一律 404——不存在随机路由。
    返回候选 dict（无 verification_status 字段：候选不是证据，入账走既有闸）。
    """
    get_hypothesis(db, user_id, hypothesis_id)  # 所有权 + 存在性（404）
    entry = _PROVIDERS.get(provider_name)
    if entry is None:
        raise NotFoundError("未知证据提供方（不在白名单）")
    _, searcher = entry
    return searcher(db, user_id, query.strip())
