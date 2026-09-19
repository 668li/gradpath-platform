"""考研情报服务层 — 院校情报存取、暗知识、研招网与分数线/调剂查询。

院校情报只做存取与检索：数据由人工审核、带官方简章源的情报经 /intel/save
写入，服务层不生成任何未经溯源的院校数据。
"""

import hashlib
import json
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.grad_intel import (
    DarkKnowledge,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
    SelfPositioning,
)

logger = logging.getLogger(__name__)

# ======================================================================
# AI 结果缓存 — 基于输入哈希，24小时 TTL
# 优化：使用 RedisCache（自动降级内存缓存），支持多 worker 共享
# 原进程内 _ai_cache dict 在多 worker 时命中率极低（~1/N）
# ======================================================================
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CACHE_PREFIX = "ai_positioning"


def _compute_cache_key(data: dict) -> str:
    """计算输入数据的哈希作为缓存键。"""
    key_fields = {
        "undergrad_tier": data.get("undergrad_tier", ""),
        "undergrad_major": data.get("undergrad_major", ""),
        "gpa": data.get("gpa"),
        "gpa_rank": data.get("gpa_rank", ""),
        "english_level": data.get("english_level", ""),
        "english_score": data.get("english_score"),
        "target_major": data.get("target_major", ""),
        "target_region": data.get("target_region", ""),
        "target_school": data.get("target_school", ""),
    }
    key_str = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cached_result(cache_key: str) -> dict | None:
    """获取缓存的 AI 结果（Redis 优先，自动降级内存缓存）。"""
    full_key = f"{CACHE_PREFIX}:{cache_key}"
    result = cache.get(full_key)
    if result is not None:
        logger.info("AI 结果缓存命中: %s", cache_key[:8])
    return result


def _set_cached_result(cache_key: str, result: dict) -> None:
    """缓存 AI 结果到 Redis。"""
    full_key = f"{CACHE_PREFIX}:{cache_key}"
    cache.set(full_key, result, ttl=CACHE_TTL_SECONDS)
    logger.info("AI 结果已缓存: %s", cache_key[:8])


def clear_positioning_cache() -> int:
    """清除所有自我定位 AI 结果缓存。

    修复 bug: 原先 API 层调用 grad_intel_service._ai_cache.clear()，
    但 _ai_cache 属性从未定义（旧实现已重构为 cache 模块），
    导致 AttributeError → 500 错误。

    Returns:
        被清除的缓存项数量
    """
    deleted = 0
    # SIM118: cache 是 RedisCache(非 dict,无 __iter__),只能走 keys() 全量扫描
    for key in cache.keys():  # noqa: SIM118
        if key.startswith(f"{CACHE_PREFIX}:"):
            if cache.delete(key):
                deleted += 1
    logger.info("已清除 %d 项自我定位 AI 缓存", deleted)
    return deleted


def get_dark_knowledge_by_stage(
    db: Session,
    stage: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[DarkKnowledge], int]:
    """获取暗知识列表，可按阶段过滤，支持分页。"""
    query = db.query(DarkKnowledge)
    if stage and stage != "all":
        query = query.filter(DarkKnowledge.stage == stage)

    # 获取总数
    total = query.count()

    # 应用分页
    offset = (page - 1) * limit
    items = (
        query.order_by(DarkKnowledge.stage, DarkKnowledge.sort_order)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return items, total


def get_dark_knowledge_stages(db: Session) -> list[dict]:
    """获取所有阶段及其条数（单次查询，避免 N+1）。"""
    from sqlalchemy import func

    stage_names = {
        "decision": "决策阶段",
        "school_selection": "择校阶段",
        "preparation": "备考阶段",
        "exam": "初试后",
        "retest": "复试阶段",
    }
    rows = (
        db.query(DarkKnowledge.stage, func.count(DarkKnowledge.id).label("count"))
        .group_by(DarkKnowledge.stage)
        .all()
    )
    return [{"stage": s, "name": stage_names.get(s, s), "count": c} for s, c in rows]


# ======================================================================
# 院校情报服务
# ======================================================================


def save_intel(db: Session, user_id: UUID, data: dict) -> GradSchoolIntel:
    """保存院校情报。"""
    intel = GradSchoolIntel(
        user_id=user_id,
        school_name=data["school_name"],
        major_name=data["major_name"],
        school_tier=data.get("school_tier", ""),
        year=data.get("year", 2026),
        background_discrimination=data.get("background_discrimination", "unknown"),
        first_choice_protection=data.get("first_choice_protection", "unknown"),
        admission_ratio=data.get("admission_ratio"),
        push_ratio=data.get("push_ratio"),
        actual_quota=data.get("actual_quota"),
        score_line=data.get("score_line"),
        retest_weight=data.get("retest_weight"),
        retest_format=data.get("retest_format"),
        score_suppression=data.get("score_suppression", "unknown"),
        transfer_friendly=data.get("transfer_friendly", "unknown"),
        insider_notes=data.get("insider_notes"),
        data_sources=data.get("data_sources", []),
        tags=data.get("tags", []),
        ai_summary=data.get("ai_summary"),
        is_ai_generated=data.get("is_ai_generated", False),
    )
    db.add(intel)
    db.commit()
    db.refresh(intel)
    return intel


def get_user_intel_list(db: Session, user_id: UUID) -> list[GradSchoolIntel]:
    """获取用户保存的所有院校情报。"""
    return (
        db.query(GradSchoolIntel)
        .filter(GradSchoolIntel.user_id == user_id)
        .order_by(GradSchoolIntel.created_at.desc())
        .all()
    )


def delete_intel(db: Session, user_id: UUID, intel_id: UUID) -> bool:
    """删除院校情报。"""
    intel = (
        db.query(GradSchoolIntel)
        .filter(GradSchoolIntel.id == intel_id, GradSchoolIntel.user_id == user_id)
        .first()
    )
    if not intel:
        return False
    db.delete(intel)
    db.commit()
    return True


# ======================================================================
# 自我定位服务
# ======================================================================


async def create_positioning(
    db: Session, user_id: UUID, data: dict, bypass_cache: bool = False
) -> SelfPositioning:
    """创建自我定位并触发 AI 评估。

    Args:
        bypass_cache: 是否绕过缓存强制重新生成
    """
    # 计算缓存键
    cache_key = _compute_cache_key(data)

    # 检查缓存（除非绕过）
    if not bypass_cache:
        cached_result = _get_cached_result(cache_key)
        if cached_result:
            logger.info("使用缓存的 AI 结果")
            # 创建定位记录但不调用 AI
            positioning = SelfPositioning(
                user_id=user_id,
                undergrad_tier=data["undergrad_tier"],
                undergrad_major=data.get("undergrad_major"),
                gpa=data.get("gpa"),
                gpa_rank=data.get("gpa_rank"),
                english_level=data.get("english_level"),
                english_score=data.get("english_score"),
                research_experience=data.get("research_experience"),
                competitions=data.get("competitions", []),
                awards=data.get("awards"),
                internships=data.get("internships"),
                target_school=data.get("target_school"),
                target_major=data.get("target_major"),
                target_region=data.get("target_region"),
                other_info=data.get("other_info"),
                ai_assessment=cached_result.get("ai_assessment"),
                reach_schools=cached_result.get("reach_schools", []),
                target_schools=cached_result.get("target_schools", []),
                safety_schools=cached_result.get("safety_schools", []),
                success_probability=cached_result.get("success_probability"),
                risk_warnings=cached_result.get("risk_warnings", []),
            )
            db.add(positioning)
            db.commit()
            db.refresh(positioning)
            return positioning

    # 创建定位记录
    positioning = SelfPositioning(
        user_id=user_id,
        undergrad_tier=data["undergrad_tier"],
        undergrad_major=data.get("undergrad_major"),
        gpa=data.get("gpa"),
        gpa_rank=data.get("gpa_rank"),
        english_level=data.get("english_level"),
        english_score=data.get("english_score"),
        research_experience=data.get("research_experience"),
        competitions=data.get("competitions", []),
        awards=data.get("awards"),
        internships=data.get("internships"),
        target_school=data.get("target_school"),
        target_major=data.get("target_major"),
        target_region=data.get("target_region"),
        other_info=data.get("other_info"),
    )
    db.add(positioning)
    db.commit()
    db.refresh(positioning)
    return positioning


def get_latest_positioning(db: Session, user_id: UUID) -> SelfPositioning | None:
    """获取用户最新的自我定位。"""
    return (
        db.query(SelfPositioning)
        .filter(SelfPositioning.user_id == user_id)
        .order_by(SelfPositioning.created_at.desc())
        .first()
    )


def get_positioning_history(db: Session, user_id: UUID) -> list[SelfPositioning]:
    """获取用户自我定位历史。"""
    return (
        db.query(SelfPositioning)
        .filter(SelfPositioning.user_id == user_id)
        .order_by(SelfPositioning.created_at.desc())
        .all()
    )


# ======================================================================
# 研招网真实数据查询
# ======================================================================


def list_yanzhao_programs(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    department: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[GradYanzhaoProgram], int]:
    """查询研招网专业目录，支持分页。"""
    query = db.query(GradYanzhaoProgram)
    if university_name:
        query = query.filter(GradYanzhaoProgram.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradYanzhaoProgram.major_name.ilike(f"%{major_name}%"))
    if department:
        query = query.filter(GradYanzhaoProgram.department.ilike(f"%{department}%"))
    if degree_type:
        query = query.filter(GradYanzhaoProgram.degree_type == degree_type)
    if year:
        query = query.filter(GradYanzhaoProgram.year == year)

    # 获取总数
    total = query.count()

    # 应用分页
    items = (
        query.order_by(GradYanzhaoProgram.university_name, GradYanzhaoProgram.major_name)
        .limit(limit)
        .offset(offset)
        .all()
    )

    return items, total


def count_yanzhao_programs(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    department: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
) -> int:
    """统计专业目录数量。"""
    query = db.query(GradYanzhaoProgram)
    if university_name:
        query = query.filter(GradYanzhaoProgram.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradYanzhaoProgram.major_name.ilike(f"%{major_name}%"))
    if department:
        query = query.filter(GradYanzhaoProgram.department.ilike(f"%{department}%"))
    if degree_type:
        query = query.filter(GradYanzhaoProgram.degree_type == degree_type)
    if year:
        query = query.filter(GradYanzhaoProgram.year == year)
    return query.count()


# 进面线来源可信判定：只信带具体溯源（URL / 数据文件）的记录。
# data_sources 里只写机构泛称（如"院校研究生院官网""研招网"）属自申报标签，
# 无法核验，一律视为不可信——宁缺勿错，假线比无线危害大十倍。
_TRACEABLE_SOURCE_RE = re.compile(r"(https?://|\.(json|csv|xlsx)\b)", re.IGNORECASE)


def scoreline_has_traceable_source(data_sources) -> bool:
    """判定分数线的 data_sources 是否含可溯源条目（URL 或数据文件名）。"""
    if not data_sources:
        return False
    if isinstance(data_sources, str):
        items = [data_sources]
    else:
        items = list(data_sources)
    return any(_TRACEABLE_SOURCE_RE.search(str(s)) for s in items)


def list_scoreline_records(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[GradScorelineRecord]:
    """查询复试分数线记录。"""
    query = db.query(GradScorelineRecord)
    if university_name:
        query = query.filter(GradScorelineRecord.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradScorelineRecord.major_name.ilike(f"%{major_name}%"))
    if degree_type:
        query = query.filter(GradScorelineRecord.degree_type == degree_type)
    if year:
        query = query.filter(GradScorelineRecord.year == year)
    records = query.all()
    # 溯源过滤：无具体溯源（URL/数据文件）的自申报来源记录不对外展示
    records = [r for r in records if scoreline_has_traceable_source(r.data_sources)]
    return sorted(
        records,
        key=lambda r: (r.university_name, r.major_name, -(r.year or 0)),
    )[offset : offset + limit]


def get_scoreline_trend(
    db: Session,
    university_name: str,
    major_name: str,
    degree_type: str | None = None,
) -> dict:
    """获取某院校某专业近年的复试分数线趋势。"""
    query = db.query(GradScorelineRecord).filter(
        GradScorelineRecord.university_name == university_name,
        GradScorelineRecord.major_name == major_name,
    )
    if degree_type:
        query = query.filter(GradScorelineRecord.degree_type == degree_type)
    records = query.order_by(GradScorelineRecord.year).all()
    # 溯源过滤：无具体溯源的记录不进趋势图（宁缺勿错）
    records = [r for r in records if scoreline_has_traceable_source(r.data_sources)]

    return {
        "university_name": university_name,
        "major_name": major_name,
        "degree_type": degree_type,
        "years": [r.year for r in records],
        "total_score_lines": [r.total_score_line for r in records],
        "politics_scores": [r.politics_score for r in records],
        "foreign_language_scores": [r.foreign_language_score for r in records],
        "business_1_scores": [r.business_1_score for r in records],
        "business_2_scores": [r.business_2_score for r in records],
        "application_counts": [r.application_count for r in records],
        "enrollment_counts": [r.enrollment_count for r in records],
    }


def list_adjustment_info(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    status: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[GradAdjustmentInfo]:
    """查询调剂信息。"""
    query = db.query(GradAdjustmentInfo)
    if university_name:
        query = query.filter(GradAdjustmentInfo.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradAdjustmentInfo.major_name.ilike(f"%{major_name}%"))
    if status:
        query = query.filter(GradAdjustmentInfo.status == status)
    if year:
        query = query.filter(GradAdjustmentInfo.year == year)
    return (
        query.order_by(
            GradAdjustmentInfo.year.desc(),
            GradAdjustmentInfo.university_name,
        )
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_school_data_summary(db: Session, university_name: str) -> dict:
    """获取某院校的数据汇总（专业数、最新分数线、趋势、调剂信息）。"""
    programs = (
        db.query(GradYanzhaoProgram)
        .filter(GradYanzhaoProgram.university_name == university_name)
        .all()
    )
    program_count = len(programs)

    latest_scoreline = (
        db.query(GradScorelineRecord)
        .filter(GradScorelineRecord.university_name == university_name)
        .order_by(GradScorelineRecord.year.desc())
        .first()
    )

    adjustments = (
        db.query(GradAdjustmentInfo)
        .filter(GradAdjustmentInfo.university_name == university_name)
        .all()
    )

    trend = "stable"
    if latest_scoreline:
        # 获取前两年数据判断趋势
        prev = (
            db.query(GradScorelineRecord)
            .filter(
                GradScorelineRecord.university_name == university_name,
                GradScorelineRecord.major_name == latest_scoreline.major_name,
                GradScorelineRecord.year == latest_scoreline.year - 1,
            )
            .first()
        )
        if prev and prev.total_score_line and latest_scoreline.total_score_line:
            diff = latest_scoreline.total_score_line - prev.total_score_line
            if diff > 10:
                trend = "up"
            elif diff < -10:
                trend = "down"

    return {
        "university_name": university_name,
        "program_count": program_count,
        "latest_year": latest_scoreline.year if latest_scoreline else None,
        "latest_scoreline": latest_scoreline.total_score_line if latest_scoreline else None,
        "scoreline_trend": trend,
        "has_adjustment": len(adjustments) > 0,
        "adjustment_count": len(adjustments),
    }


# ======================================================================
# 院校官方公告归口 — 已 APPROVED 研招公告按域名后缀归口到院校
# ======================================================================
# 归口键：研招公告 source_url 的注册域名后缀（学院级域名也被后缀自动覆盖，
# 如 csyh.sdu.edu.cn 命中 sdu.edu.cn -> 山东大学）。
# 只维护实际有公告的院校，自包含、无爬虫导入耦合。
_ANNOUNCE_DOMAIN_SCHOOL: dict[str, str] = {
    "nankai.edu.cn": "南开大学",
    "scnu.edu.cn": "华南师范大学",
    "sdu.edu.cn": "山东大学",
    "sdust.edu.cn": "山东科技大学",
    "sustech.edu.cn": "南方科技大学",
    "swjtu.edu.cn": "西南交通大学",
    "tju.edu.cn": "天津大学",
    "dhu.edu.cn": "东华大学",
    "seu.edu.cn": "东南大学",
    "cau.edu.cn": "中国农业大学",
    "tongji.edu.cn": "同济大学",
    "nenu.edu.cn": "东北师范大学",
    "nudt.edu.cn": "国防科技大学",
    "scut.edu.cn": "华南理工大学",
    "snnu.edu.cn": "陕西师范大学",
    "hust.edu.cn": "华中科技大学",
    "ecnu.edu.cn": "华东师范大学",
    # zs.gs.upc.edu.cn 校区歧义已解歧：该域公告标题均写明"中国石油大学（华东）"
    # （如"中国石油大学（华东）2026年…成绩查询及复核通知"），归口华东校区。
    "zs.gs.upc.edu.cn": "中国石油大学（华东）",
}

# 明确不归口：教育部 / 第三方聚合 / 公众号
_ANNOUNCE_SKIP_DOMAINS = {
    "www.moe.gov.cn",  # 教育部政策，非院校
    "yz.kaoyan.com",  # 第三方聚合
    "mp.weixin.qq.com",  # 公众号，非院校官方域
}


def get_school_announcements(db: Session, school_name: str, limit: int = 20) -> list[dict]:
    """获取归口到某院校的已审核官方公告（研招公告类别）。

    归口规则（只认真实数据，宁可少不可错）：
    1. source_url 域名后缀命中该校（学院级域名由后缀自动覆盖）
    2. 跳过教育部 / 第三方聚合 / 公众号域名
    3. 只取 status=approved 的公告
    """
    from app.models.kaoyan_news import KaoyanNews

    news = (
        db.query(KaoyanNews)
        .filter(
            KaoyanNews.status == "approved",
            KaoyanNews.category.like("研招公告%"),
        )
        .order_by(
            KaoyanNews.published_at.desc().nullslast(),
            KaoyanNews.created_at.desc(),
        )
        .all()
    )

    results: list[dict] = []
    for item in news:
        if len(results) >= limit:
            break
        m = re.match(r"https?://([^/]+)", item.source_url or "")
        host = (m.group(1).lower() if m else "") or ""
        # 域名后缀匹配
        matched = None
        for suffix, sname in _ANNOUNCE_DOMAIN_SCHOOL.items():
            if host == suffix or host.endswith("." + suffix):
                matched = sname
                break
        if not matched:
            continue
        # 跳过明确不归口域名（校区歧义/第三方）
        if any(skip in host for skip in _ANNOUNCE_SKIP_DOMAINS):
            continue
        if matched != school_name:
            continue
        results.append(
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "source_url": item.source_url,
                "source_platform": item.source_platform,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "category": item.category,
                "quality_grade": item.quality_grade,
            }
        )
    return results
