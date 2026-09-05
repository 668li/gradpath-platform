# backend/app/api/assessment.py
"""职业测评 API 路由 — 支持 5 种测评体系。

- GET /api/assessment/questions — 获取题目列表（可选 type 参数，默认 holland，无需认证）
- POST /api/assessment/submit — 提交答案，计算结果并保存
- GET /api/assessment/result — 获取最近一次测评结果
- GET /api/assessment/history — 获取历史记录
- POST /api/assessment/interpret — 测评 × 专有报考数据 → 专属路径解读（护城河）

支持的测评类型：holland | mbti | big_five | big_five_short | disc
"""

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.deps import get_current_user
from app.database import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.schemas.assessment import AssessmentResponse, AssessmentSubmit, Question
from app.services.assessment_interpret_service import build_interpretation
from app.services.assessment_service import ASSESSMENT_CALCULATORS, ASSESSMENT_QUESTIONS

router = APIRouter(prefix="/api/assessment", tags=["职业测评"])

# 合法测评类型集合
_VALID_TYPES = set(ASSESSMENT_QUESTIONS.keys())

# 霍兰德平 profile 判定阈值：六维计数排序后"第1名−第4名"≤此值 → 结果无区分度。
# 48 题/6 维≈每维 8 分，阈值 2 为拍板默认值，调整只改这一个常量。
_HOLLAND_FLAT_GAP = 2

# 每种测评每题的合法答案取值（用于完整性 + 取值合法性校验）
_ASSESSMENT_ANSWER_VALUES = {
    "holland": {"R", "I", "A", "S", "E", "C"},
    "mbti": {"E", "I", "S", "N", "T", "F", "J", "P"},
    "big_five": {str(i) for i in range(1, 6)},  # Likert 1~5
    "big_five_short": {str(i) for i in range(1, 6)},  # Likert 1~5（短版）
    "disc": {"D", "I", "S", "C"},
}


def _compute_scores_fallback(assessment_type: str, answers: dict) -> dict[str, float]:
    """旧数据（scores 列未回填前）按 answers 实时计算维度分。"""
    calculator = ASSESSMENT_CALCULATORS.get(assessment_type)
    if not calculator:
        return {}
    result = calculator(answers)
    return {k: float(v) for k, v in (result.get("scores") or {}).items()}


def _to_response(assessment: Assessment) -> AssessmentResponse:
    """将 Assessment ORM 对象组装为响应。

    scores 优先读入库的维度分（真实语义：大五为均分 dict[str,float]），
    旧行或缺失时按 answers 实时回填，保证响应里的分数永远是对的。
    """
    scores = assessment.scores or _compute_scores_fallback(
        assessment.assessment_type, assessment.answers or {}
    )
    return AssessmentResponse(
        id=assessment.id,
        assessment_type=assessment.assessment_type,
        result_code=assessment.result_code,
        result_summary=assessment.result_summary,
        recommended_directions=assessment.recommended_directions or [],
        scores=scores,
        created_at=assessment.created_at,
    )


def _validate_answers(assessment_type: str, answers: dict) -> list[str]:
    """校验答案完整性与作答可信度，返回警告列表（空列表 = 完全正常）。

    完整性：必须覆盖该类型全部题目且取值合法（防止只交几题就出结果）。
    可信度：作答模式异常（答全但大量同一答案 / 大五方差过小）→ 附信度警示，
    把"防作弊/防乱答"从仅前端搬到后端，杜绝绕开前端直接打接口。
    所有题目数据是内置常量，无需查库。
    """
    warnings: list[str] = []
    questions = ASSESSMENT_QUESTIONS.get(assessment_type) or []
    required_ids = {q["id"] for q in questions}
    submitted_ids = set(answers.keys())
    legal_values = _ASSESSMENT_ANSWER_VALUES.get(assessment_type, set())

    missing = required_ids - submitted_ids
    extra = submitted_ids - required_ids
    illegal = {
        qid for qid, val in answers.items() if qid in required_ids and val not in legal_values
    }
    if missing:
        warnings.append(
            f"缺失 {len(missing)} 题未作答（如 {sorted(missing)[:3]}），结果不完整、仅供参考。"
        )
    if extra:
        warnings.append(f"存在 {len(extra)} 个未知题号（{sorted(extra)[:3]}），已忽略。")
    if illegal:
        warnings.append(f"{len(illegal)} 题答案取值非法，已忽略。")
    if required_ids and not missing:
        # 完整作答仍全同/极低区分度 → 存疑（诚实标注，不武断判作弊）
        values = [answers[qid] for qid in sorted(required_ids) if qid in answers]
        unique = len({v for v in values if v in legal_values})
        if unique <= 1:
            warnings.append("你的作答几乎都为同一选项，结果可能偏颇，解读时请留意。")
        if assessment_type in ("big_five", "big_five_short"):
            nums = [
                int(answers[qid])
                for qid in required_ids
                if qid in answers and answers[qid] in legal_values
            ]
            if len(nums) >= 5:
                variance = sum((x - sum(nums) / len(nums)) ** 2 for x in nums) / len(nums)
                if variance < 0.3:
                    warnings.append("你的作答选项集中在很小范围内，结果区分度低，仅供参考。")
        if assessment_type == "holland":
            # 平 profile 诚实降级：六维计数无拉开差距 → top3 代码是随机排序的产物，
            # 不配当决策依据，如实标注并引导以下方真实数据解读为准（不篡改 result_code）。
            counts = Counter(v for v in values if v in legal_values)
            dims = sorted((counts.get(d, 0) for d in "RIASEC"), reverse=True)
            if dims[0] - dims[3] <= _HOLLAND_FLAT_GAP:
                warnings.append(
                    "你的各维度作答接近，本次结果区分度较低，请以下方真实数据解读为准。"
                )
    return warnings


@router.get("/questions", response_model=list[Question])
def get_questions(type: str = Query("holland", description="测评类型：holland|mbti|big_five|big_five_short|disc")):
    """获取指定类型的测评题目列表（无需认证）。

    不传 type 时默认返回霍兰德题目，保持向后兼容。
    """
    questions = ASSESSMENT_QUESTIONS.get(type)
    if questions is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的测评类型: {type}，可选值: {sorted(_VALID_TYPES)}",
        )
    return questions


@router.post(
    "/submit",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_assessment(
    body: AssessmentSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交答案，计算结果并保存到数据库。

    根据 body.assessment_type 调用对应的计算函数；先做后端答案校验，
    把信度警示与结果一并返回（不阻断提交，但如实标注）。
    """
    assessment_type = body.assessment_type
    calculator = ASSESSMENT_CALCULATORS.get(assessment_type)
    if calculator is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的测评类型: {assessment_type}，可选值: {sorted(_VALID_TYPES)}",
        )

    warnings = _validate_answers(assessment_type, body.answers)
    result = calculator(body.answers)
    result_summary = result["result_summary"]
    if warnings:
        result_summary += "\n\n【作答提示】" + "；".join(warnings)

    assessment = Assessment(
        user_id=user.id,
        assessment_type=assessment_type,
        answers=body.answers,
        result_code=result["result_code"],
        result_summary=result_summary,
        recommended_directions=result["recommended_directions"],
        scores=result["scores"],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    # 失效用户上下文缓存（build_user_context 依赖最新 Assessment）
    try:
        cache.delete(f"user_context:{user.id}")
    except Exception:
        pass
    return _to_response(assessment)


@router.get("/result", response_model=AssessmentResponse | None)
def get_latest_result(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取最近一次测评结果，不存在则返回 null。"""
    assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not assessment:
        return None
    return _to_response(assessment)


@router.get("/history", response_model=list[AssessmentResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取历史测评记录（按创建时间倒序）。"""
    assessments = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .all()
    )
    return [_to_response(a) for a in assessments]


@router.post("/interpret")
def interpret_assessment(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """测评 × 专有报考数据 → 专属路径解读（护城河）。

    读最新测评 + 个人档案（专业/学校层次/应届/目标方向），
    结合真实报考数据（三路决策、进面线、薪资前景、同分人群去向）产出专属解读。
    未完成测评时返回 has_assessment=False 引导补全，不报错。
    """
    return build_interpretation(db, user.id)
