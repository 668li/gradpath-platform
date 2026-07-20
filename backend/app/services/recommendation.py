"""AI 推荐服务 — 基于内容的院校推荐、调剂推荐、暗知识推荐。

推荐策略：
1. 内容匹配：根据用户分数/地区/层次/专业匹配院校
2. 调剂机会：基于分数差、专业匹配度推荐调剂
3. 暗知识：按备考阶段推荐相关盲区知识
"""
import logging
from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.grad_intel import (
    DarkKnowledge,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
)
from app.models.school import School

logger = logging.getLogger(__name__)

TIER_ORDER = {"985": 0, "211": 1, "双一流": 2, "普通": 3}


@dataclass
class SchoolRecommendation:
    """单个院校推荐结果。"""
    name: str
    province: str = ""
    level: str = ""
    match_score: float = 0.0
    match_reasons: list[str] = field(default_factory=list)
    score_line: int | None = None
    adjustment_available: bool = False


@dataclass
class AdjustmentRecommendation:
    """调剂推荐结果。"""
    university_name: str
    department: str
    major_name: str
    match_score: float = 0.0
    match_reasons: list[str] = field(default_factory=list)
    adjustment_quota: int | None = None
    deadline: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    source_url: str | None = None


@dataclass
class DarkKnowledgeRecommendation:
    """暗知识推荐结果。"""
    id: str
    stage: str
    category: str
    title: str
    content: str
    importance: str
    common_misconception: str | None = None
    actionable_advice: str | None = None
    relevance_score: float = 0.0


class ContentBasedRecommender:
    """基于内容的推荐引擎。

    通过多维度匹配（分数、层次、地区、专业）计算推荐得分。
    """

    def __init__(self, db: Session):
        self.db = db

    def recommend_schools(
        self,
        target_score: int | None = None,
        target_tier: str | None = None,
        target_region: str | None = None,
        target_major: str | None = None,
        top_n: int = 10,
    ) -> list[SchoolRecommendation]:
        """根据目标条件推荐匹配的院校。

        Args:
            target_score: 用户目标分数
            target_tier: 目标院校层次 (985/211/双一流/普通)
            target_region: 目标地区（省份）
            target_major: 目标专业
            top_n: 返回前 N 条结果
        """
        cache_key = f"rec:schools:{target_score}:{target_tier}:{target_region}:{target_major}:{top_n}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 优化查询：只获取每个院校专业的最新一条分数线记录
        from sqlalchemy import func, case
        from sqlalchemy.orm import aliased

        # 子查询：获取每个 university_name|major_name 的最新年份
        latest_year_subq = (
            self.db.query(
                GradScorelineRecord.university_name,
                GradScorelineRecord.major_name,
                func.max(GradScorelineRecord.year).label("max_year"),
            )
            .group_by(
                GradScorelineRecord.university_name,
                GradScorelineRecord.major_name,
            )
            .subquery()
        )

        # 主查询：使用 JOIN 只获取最新记录
        scoreline_query = (
            self.db.query(GradScorelineRecord)
            .join(
                latest_year_subq,
                (GradScorelineRecord.university_name == latest_year_subq.c.university_name)
                & (GradScorelineRecord.major_name == latest_year_subq.c.major_name)
                & (GradScorelineRecord.year == latest_year_subq.c.max_year),
            )
        )

        if target_major:
            scoreline_query = scoreline_query.filter(
                GradScorelineRecord.major_name.ilike(f"%{target_major}%")
            )

        if target_region:
            # 联合查询 School 表按省份过滤
            scoreline_query = scoreline_query.join(
                School, School.name == GradScorelineRecord.university_name
            ).filter(School.province.ilike(f"%{target_region}%"))

        scorelines = scoreline_query.limit(500).all()

        # 构建调剂信息索引
        adj_query = self.db.query(GradAdjustmentInfo).filter(
            GradAdjustmentInfo.status == "open"
        )
        if target_major:
            adj_query = adj_query.filter(
                GradAdjustmentInfo.major_name.ilike(f"%{target_major}%")
            )
        adjustments = adj_query.all()
        adj_map: dict[str, list[GradAdjustmentInfo]] = {}
        for adj in adjustments:
            adj_map.setdefault(adj.university_name, []).append(adj)

        # 按需查询 School 信息（只查匹配的院校）
        matched_unis = {sl.university_name for sl in scorelines}
        schools = self.db.query(School).filter(School.name.in_(matched_unis)).all()
        school_map: dict[str, School] = {s.name: s for s in schools}

        results: list[SchoolRecommendation] = []
        seen = set()

        for sl in scorelines:
            uni = sl.university_name
            if uni in seen:
                continue
            seen.add(uni)

            school = school_map.get(uni)
            reasons: list[str] = []
            score = 0.0

            # 分数匹配 (0-40分)
            if target_score is not None and sl.total_score_line is not None:
                diff = target_score - sl.total_score_line
                if -20 <= diff <= 20:
                    score += 40 - abs(diff) * 2
                    reasons.append(f"目标分数{target_score}与复试线{sl.total_score_line}差距{diff}分")
                elif -40 <= diff < -20:
                    score += 10
                    reasons.append(f"目标分数低于复试线{abs(diff)}分，有挑战")
                elif 20 < diff <= 40:
                    score += 25
                    reasons.append(f"目标分数高于复试线{diff}分，较为稳妥")
                else:
                    score += 5
            elif target_score is not None and sl.total_score_line is None:
                score += 15
                reasons.append("暂无复试线数据")

            # 层次匹配 (0-25分)
            if target_tier and school and school.level:
                if school.level == target_tier:
                    score += 25
                    reasons.append(f"层次匹配: {school.level}")
                elif TIER_ORDER.get(school.level, 99) < TIER_ORDER.get(target_tier, 99):
                    score += 15
                    reasons.append(f"院校层次({school.level})优于目标({target_tier})")
                else:
                    score += 10
                    reasons.append(f"院校层次({school.level})低于目标({target_tier})")

            # 地区匹配 (0-20分)
            if target_region and school and school.province:
                if target_region in school.province or school.province in target_region:
                    score += 20
                    reasons.append(f"地区匹配: {school.province}")
                else:
                    score += 5
            elif target_region is None:
                score += 10

            # 专业匹配 (0-15分)
            if target_major:
                if target_major in sl.major_name or sl.major_name in target_major:
                    score += 15
                    reasons.append(f"专业匹配: {sl.major_name}")
                else:
                    score += 8

            has_adj = uni in adj_map

            results.append(SchoolRecommendation(
                name=uni,
                province=school.province if school else "",
                level=school.level if school else "",
                match_score=round(score, 1),
                match_reasons=reasons,
                score_line=sl.total_score_line,
                adjustment_available=has_adj,
            ))

        results.sort(key=lambda x: x.match_score, reverse=True)
        top = results[:top_n]
        cache.set(cache_key, top, ttl=180)
        return top

    def recommend_adjustments(
        self,
        target_score: int | None = None,
        target_major: str | None = None,
        target_region: str | None = None,
        top_n: int = 10,
    ) -> list[AdjustmentRecommendation]:
        """推荐调剂机会。"""
        cache_key = f"rec:adj:{target_score}:{target_major}:{target_region}:{top_n}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        query = self.db.query(GradAdjustmentInfo).filter(
            GradAdjustmentInfo.status == "open"
        )
        if target_major:
            query = query.filter(
                GradAdjustmentInfo.major_name.ilike(f"%{target_major}%")
            )
        adjustments = query.all()

        # 查询 School 表获取省份
        school_map: dict[str, School] = {}
        if target_region:
            schools = self.db.query(School).filter(
                School.province.ilike(f"%{target_region}%")
            ).all()
            for s in schools:
                school_map[s.name] = s

        results: list[AdjustmentRecommendation] = []

        for adj in adjustments:
            reasons: list[str] = []
            score = 0.0

            # 名额匹配
            if adj.adjustment_quota and adj.adjustment_quota > 0:
                score += 20
                reasons.append(f"调剂名额: {adj.adjustment_quota}")

            # 地区匹配
            if target_region:
                school = school_map.get(adj.university_name)
                if school and school.province and (
                    target_region in school.province or school.province in target_region
                ):
                    score += 30
                    reasons.append(f"地区匹配: {school.province}")
                else:
                    score += 5

            # 专业匹配
            if target_major:
                if target_major in adj.major_name or adj.major_name in target_major:
                    score += 30
                    reasons.append(f"专业匹配: {adj.major_name}")
                else:
                    score += 5

            # 有联系方式
            if adj.contact_email or adj.contact_phone:
                score += 10
                reasons.append("有联系方式")

            # 截止日期信息
            if adj.deadline:
                score += 5
                reasons.append(f"截止日期: {adj.deadline}")

            # 原专业范围信息
            if adj.original_major_range:
                score += 5
                reasons.append(f"可调专业范围: {adj.original_major_range}")

            results.append(AdjustmentRecommendation(
                university_name=adj.university_name,
                department=adj.department,
                major_name=adj.major_name,
                match_score=round(score, 1),
                match_reasons=reasons,
                adjustment_quota=adj.adjustment_quota,
                deadline=adj.deadline,
                contact_email=adj.contact_email,
                contact_phone=adj.contact_phone,
                source_url=adj.source_url,
            ))

        results.sort(key=lambda x: x.match_score, reverse=True)
        top = results[:top_n]
        cache.set(cache_key, top, ttl=300)
        return top

    def recommend_dark_knowledge(
        self,
        stage: str | None = None,
        top_n: int = 10,
    ) -> list[DarkKnowledgeRecommendation]:
        """推荐暗知识，按阶段过滤。"""
        cache_key = f"rec:dk:{stage}:{top_n}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        query = self.db.query(DarkKnowledge)
        if stage:
            query = query.filter(DarkKnowledge.stage == stage)

        items = query.order_by(
            DarkKnowledge.sort_order,
        ).limit(top_n).all()

        results = []
        for item in items:
            relevance = 0.0
            if item.importance == "critical":
                relevance = 100.0
            elif item.importance == "high":
                relevance = 80.0
            else:
                relevance = 60.0

            results.append(DarkKnowledgeRecommendation(
                id=str(item.id),
                stage=item.stage,
                category=item.category,
                title=item.title,
                content=item.content,
                importance=item.importance,
                common_misconception=item.common_misconception,
                actionable_advice=item.actionable_advice,
                relevance_score=relevance,
            ))

        results.sort(key=lambda x: x.relevance_score, reverse=True)
        cache.set(cache_key, results, ttl=300)
        return results
