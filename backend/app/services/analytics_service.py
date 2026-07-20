"""数据分析服务 — 分数线趋势、录取率、报录比、调剂分析。"""
import logging
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.models.grad_intel import GradAdjustmentInfo, GradScorelineRecord, GradSchoolIntel
from app.models.school import School

logger = logging.getLogger(__name__)


class AnalyticsService:
    """考研数据分析服务。"""

    def __init__(self, db: Session):
        self.db = db

    # ==================================================================
    # 分数线趋势分析
    # ==================================================================

    def get_scoreline_trend(
        self, university_name: str, major_name: str
    ) -> dict[str, Any]:
        """获取分数线多年趋势。"""
        records = (
            self.db.query(GradScorelineRecord)
            .filter(
                GradScorelineRecord.university_name == university_name,
                GradScorelineRecord.major_name == major_name,
            )
            .order_by(GradScorelineRecord.year)
            .all()
        )

        if not records:
            return {"error": "未找到该院校专业的分数线数据"}

        years = [r.year for r in records]
        total_scores = [r.total_score_line for r in records]
        politics = [r.politics_score for r in records]
        english = [r.foreign_language_score for r in records]
        business_1 = [r.business_1_score for r in records]
        business_2 = [r.business_2_score for r in records]

        # 趋势分析
        trend_analysis = self._calculate_trend(total_scores)
        yoy_change = self._calculate_yoy_change(total_scores)

        return {
            "university": university_name,
            "major": major_name,
            "years": years,
            "total_scores": total_scores,
            "politics": politics,
            "english": english,
            "business_1": business_1,
            "business_2": business_2,
            "trend_analysis": trend_analysis,
            "year_over_year_change": yoy_change,
            "statistics": {
                "avg_score": round(np.mean([s for s in total_scores if s]), 1)
                if total_scores
                else 0,
                "max_score": max([s for s in total_scores if s], default=0),
                "min_score": min([s for s in total_scores if s], default=0),
                "std_score": round(
                    np.std([s for s in total_scores if s]), 1
                )
                if total_scores
                else 0,
            },
        }

    def _calculate_trend(self, scores: list[int | None]) -> dict:
        """计算分数线趋势（线性回归）。"""
        valid_scores = [s for s in scores if s is not None]
        if len(valid_scores) < 2:
            return {"trend": "insufficient_data", "slope": 0}

        try:
            from sklearn.linear_model import LinearRegression

            X = np.array(range(len(valid_scores))).reshape(-1, 1)
            y = np.array(valid_scores)
            model = LinearRegression().fit(X, y)
            slope = model.coef_[0]

            if slope > 2:
                trend = "rising"
            elif slope < -2:
                trend = "falling"
            else:
                trend = "stable"

            return {
                "trend": trend,
                "slope": round(float(slope), 2),
                "description": f"分数线{'持续上升' if trend == 'rising' else '持续下降' if trend == 'falling' else '相对稳定'}，年均变化 {slope:.1f} 分",
            }
        except Exception as e:
            logger.error("趋势计算失败: %s", e)
            return {"trend": "calculation_error", "slope": 0}

    def _calculate_yoy_change(self, scores: list[int | None]) -> list[float | None]:
        """计算年同比变化。"""
        changes = [None]
        for i in range(1, len(scores)):
            if scores[i] is not None and scores[i - 1] is not None:
                change = scores[i] - scores[i - 1]
                changes.append(float(change))
            else:
                changes.append(None)
        return changes

    # ==================================================================
    # 录取率分析
    # ==================================================================

    def get_admission_rate(
        self,
        university_name: str | None = None,
        major_name: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any]:
        """获取录取率分析。"""
        query = self.db.query(GradScorelineRecord).filter(
            GradScorelineRecord.application_count.isnot(None),
            GradScorelineRecord.enrollment_count.isnot(None),
            GradScorelineRecord.application_count > 0,
        )

        if university_name:
            query = query.filter(
                GradScorelineRecord.university_name == university_name
            )
        if major_name:
            query = query.filter(GradScorelineRecord.major_name == major_name)
        if year:
            query = query.filter(GradScorelineRecord.year == year)

        records = query.all()

        details = []
        for r in records:
            rate = (r.enrollment_count / r.application_count * 100) if r.application_count else 0
            details.append(
                {
                    "university": r.university_name,
                    "major": r.major_name,
                    "year": r.year,
                    "admission_rate": round(rate, 2),
                    "enrollment": r.enrollment_count,
                    "applications": r.application_count,
                    "competition_ratio": round(
                        r.application_count / r.enrollment_count, 1
                    )
                    if r.enrollment_count
                    else 0,
                }
            )

        # 汇总统计
        rates = [d["admission_rate"] for d in details]
        avg_rate = np.mean(rates) if rates else 0

        return {
            "details": details,
            "summary": {
                "average_rate": round(float(avg_rate), 2),
                "total_programs": len(
                    set((d["university"], d["major"]) for d in details)
                ),
                "competition_level": self._classify_competition(float(avg_rate)),
                "best_rate": max(rates) if rates else 0,
                "worst_rate": min(rates) if rates else 0,
            },
        }

    def _classify_competition(self, rate: float) -> str:
        """根据录取率分类竞争程度。"""
        if rate > 30:
            return "low"  # 低竞争
        elif rate > 15:
            return "medium"  # 中等竞争
        elif rate > 8:
            return "high"  # 高竞争
        else:
            return "extreme"  # 极高竞争

    # ==================================================================
    # 报录比分析
    # ==================================================================

    def get_application_ratio(
        self, year: int | None = None, top_n: int = 20
    ) -> dict[str, Any]:
        """获取报录比分析 — 热门/冷门专业排名。"""
        query = self.db.query(GradScorelineRecord).filter(
            GradScorelineRecord.application_count.isnot(None),
            GradScorelineRecord.application_count > 0,
            GradScorelineRecord.enrollment_count.isnot(None),
            GradScorelineRecord.enrollment_count > 0,
        )

        if year:
            query = query.filter(GradScorelineRecord.year == year)

        records = query.all()

        ratios = []
        for r in records:
            ratio = r.application_count / r.enrollment_count
            ratios.append(
                {
                    "university": r.university_name,
                    "major": r.major_name,
                    "year": r.year,
                    "ratio": round(ratio, 1),
                    "applications": r.application_count,
                    "enrollment": r.enrollment_count,
                }
            )

        # 按报录比排序
        ratios.sort(key=lambda x: x["ratio"], reverse=True)

        # 统计
        ratio_values = [r["ratio"] for r in ratios]

        return {
            "hot_programs": ratios[:top_n],
            "cold_programs": ratios[-top_n:] if len(ratios) >= top_n else [],
            "statistics": {
                "avg_ratio": round(float(np.mean(ratio_values)), 1)
                if ratio_values
                else 0,
                "max_ratio": ratios[0]["ratio"] if ratios else 0,
                "min_ratio": ratios[-1]["ratio"] if ratios else 0,
                "median_ratio": round(float(np.median(ratio_values)), 1)
                if ratio_values
                else 0,
                "total_programs": len(ratios),
            },
        }

    # ==================================================================
    # 调剂成功率分析
    # ==================================================================

    def get_adjustment_analysis(
        self, university_name: str | None = None
    ) -> dict[str, Any]:
        """获取调剂成功率分析。"""
        # 调剂信息
        adjustment_query = self.db.query(GradAdjustmentInfo)
        if university_name:
            adjustment_query = adjustment_query.filter(
                GradAdjustmentInfo.university_name == university_name
            )
        adjustments = adjustment_query.all()

        # 院校情报（调剂友好度）
        intel_query = self.db.query(GradSchoolIntel).filter(
            GradSchoolIntel.transfer_friendly != "unknown"
        )
        if university_name:
            intel_query = intel_query.filter(
                GradSchoolIntel.school_name == university_name
            )
        intel_records = intel_query.all()

        # 统计调剂友好度
        friendly_count = sum(
            1 for i in intel_records if i.transfer_friendly == "yes"
        )
        moderate_count = sum(
            1 for i in intel_records if i.transfer_friendly == "moderate"
        )
        unfriendly_count = sum(
            1 for i in intel_records if i.transfer_friendly == "no"
        )
        total = len(intel_records)

        # 调剂友好院校列表
        friendly_schools = [
            {
                "school": i.school_name,
                "major": i.major_name,
                "transfer_friendly": i.transfer_friendly,
                "insider_notes": i.insider_notes,
                "admission_ratio": i.admission_ratio,
            }
            for i in intel_records
            if i.transfer_friendly == "yes"
        ][:20]

        return {
            "adjustment_programs": len(adjustments),
            "adjustment_details": [
                {
                    "university": a.university_name,
                    "department": a.department,
                    "major": a.major_name,
                    "quota": a.adjustment_quota,
                    "status": a.status,
                }
                for a in adjustments
            ],
            "friendly_stats": {
                "friendly": friendly_count,
                "moderate": moderate_count,
                "unfriendly": unfriendly_count,
                "total": total,
                "friendly_rate": round(friendly_count / total * 100, 2)
                if total
                else 0,
            },
            "top_friendly_schools": friendly_schools,
            "recommendations": self._generate_adjustment_tips(
                adjustments, intel_records
            ),
        }

    def _generate_adjustment_tips(
        self, adjustments: list, intel_records: list
    ) -> list[str]:
        """生成调剂建议。"""
        tips = []

        if not adjustments:
            tips.append("当前暂无调剂信息，建议关注研招网和院校官网的调剂公告")

        friendly_count = sum(
            1 for i in intel_records if i.transfer_friendly == "yes"
        )
        if friendly_count > 0:
            tips.append(f"共有 {friendly_count} 所院校被标记为调剂友好")

        # 检查是否有压分现象
        score_suppressed = sum(
            1 for i in intel_records if i.score_suppression == "yes"
        )
        if score_suppressed > 0:
            tips.append(f"注意：有 {score_suppressed} 所院校存在压分现象，调剂时需谨慎")

        return tips


def get_analytics_service(db: Session) -> AnalyticsService:
    """获取分析服务实例。"""
    return AnalyticsService(db)
