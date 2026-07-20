"""AI 智能学习计划 API"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.study_plan import StudyPlan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-study-plan", tags=["AI 学习计划"])


# ============ Schemas ============
class GeneratePlanRequest(BaseModel):
    """生成学习计划请求"""
    target_school: str = Field(..., min_length=1, max_length=200, description="目标院校")
    target_major: str = Field(..., min_length=1, max_length=200, description="目标专业")
    current_score: int = Field(..., ge=0, le=750, description="当前分数（预估）")
    target_score: int = Field(..., ge=0, le=750, description="目标分数")
    weak_subjects: list[str] = Field(default_factory=list, description="薄弱科目")
    exam_date: str = Field(..., description="考试日期 (YYYY-MM-DD)")
    study_hours_per_day: int = Field(default=8, ge=1, le=16, description="每日学习时长")

    @validator("target_score")
    def target_must_exceed_current(cls, v, values):
        if "current_score" in values and v <= values["current_score"]:
            raise ValueError("目标分数必须大于当前分数")
        return v

    @validator("exam_date")
    def exam_date_must_be_future(cls, v):
        try:
            exam = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("日期格式错误，请使用 YYYY-MM-DD")
        if exam <= datetime.now().date():
            raise ValueError("考试日期必须在未来")
        return v


class SubjectPlan(BaseModel):
    """科目计划"""
    subject: str
    daily_hours: float
    tasks: list[str]


class WeeklyPlan(BaseModel):
    """周计划"""
    week: int
    subjects: list[SubjectPlan]
    weekly_test: str
    milestone: str


class Phase(BaseModel):
    """阶段计划"""
    name: str
    duration_days: int
    weekly_plan: list[WeeklyPlan]
    goals: list[str]


class DailySchedule(BaseModel):
    """每日时间安排"""
    morning: str
    afternoon: str
    evening: str


class GeneratePlanResponse(BaseModel):
    """生成学习计划响应"""
    total_days: int
    target_school: str
    target_major: str
    current_score: int
    target_score: int
    phases: list[Phase]
    daily_schedule: DailySchedule
    tips: list[str]
    ai_summary: str


class SavePlanRequest(BaseModel):
    """保存学习计划请求"""
    plan_data: GeneratePlanRequest
    generated_plan: dict


class ProgressUpdate(BaseModel):
    """进度更新"""
    week: int
    completed_tasks: list[str]


# ============ Plan Generation Logic ============
SUBJECTS = {
    "政治": {"name": "政治", "start_month": 3, "daily_hours_range": (1.5, 3)},
    "英语": {"name": "英语", "start_month": 1, "daily_hours_range": (2, 3)},
    "数学": {"name": "数学", "start_month": 1, "daily_hours_range": (3, 4)},
    "专业课": {"name": "专业课", "start_month": 1, "daily_hours_range": (2, 4)},
}


def _calculate_phases(total_days: int) -> list[dict]:
    """将备考周期分为三个阶段：基础、强化、冲刺"""
    basic_days = int(total_days * 0.4)
    strengthen_days = int(total_days * 0.3)
    sprint_days = total_days - basic_days - strengthen_days
    
    return [
        {"name": "基础阶段", "duration_days": basic_days, "description": "系统学习，打牢基础"},
        {"name": "强化阶段", "duration_days": strengthen_days, "description": "重点突破，查漏补缺"},
        {"name": "冲刺阶段", "duration_days": sprint_days, "description": "模拟实战，调整状态"},
    ]


def _generate_weekly_tasks(subject: str, phase: str, week_in_phase: int, is_weak: bool) -> list[str]:
    """根据科目、阶段和周数生成任务"""
    tasks = []
    
    if subject == "数学":
        if phase == "基础阶段":
            tasks = ["完成高等数学教材习题", "每日练习10道计算题", "整理错题本"]
        elif phase == "强化阶段":
            tasks = ["完成强化班讲义", "每日练习15道综合题", "专题突破训练"]
        else:
            tasks = ["完成近5年真题", "模拟考试训练", "查漏补缺"]
    elif subject == "英语":
        if phase == "基础阶段":
            tasks = ["每日背诵50个单词", "阅读理解2篇", "语法专项练习"]
        elif phase == "强化阶段":
            tasks = ["每日背诵30个单词", "阅读理解3篇", "翻译练习1篇"]
        else:
            tasks = ["完成真题套卷", "作文模板背诵", "模拟考试"]
    elif subject == "政治":
        if phase == "基础阶段":
            tasks = ["观看基础班视频", "整理知识框架", "做章节练习"]
        elif phase == "强化阶段":
            tasks = ["重点章节精讲", "选择题专项训练", "时政热点整理"]
        else:
            tasks = ["背诵大题答案", "模拟考试训练", "时政热点汇总"]
    elif subject == "专业课":
        if phase == "基础阶段":
            tasks = ["通读教材", "整理笔记", "基础概念理解"]
        elif phase == "强化阶段":
            tasks = ["重点章节深入", "真题研究", "专题整理"]
        else:
            tasks = ["真题模拟", "重点知识背诵", "查漏补缺"]
    
    if is_weak and week_in_phase % 2 == 0:
        tasks.append("额外加练薄弱知识点")
    
    return tasks


def _generate_plan(request: GeneratePlanRequest) -> GeneratePlanResponse:
    """生成个性化学习计划"""
    # 计算距离考试的天数
    try:
        exam_date = datetime.strptime(request.exam_date, "%Y-%m-%d").date()
        today = datetime.now().date()
        total_days = (exam_date - today).days
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    
    if total_days <= 0:
        raise HTTPException(status_code=400, detail="考试日期必须在未来")
    
    if total_days < 30:
        raise HTTPException(status_code=400, detail="备考时间过短，建议至少30天")
    
    # 生成阶段
    phases_data = _calculate_phases(total_days)
    
    # 确定科目列表
    subjects = ["数学", "英语", "专业课"]
    if total_days > 90:
        subjects.append("政治")  # 政治一般最后3个月开始
    
    # 计算各科目每日时长分配
    weak_set = set(request.weak_subjects)
    subject_hours = {}
    total_weight = 0
    
    for subject in subjects:
        if subject in weak_set:
            weight = 1.5  # 薄弱科目加权
        else:
            weight = 1.0
        subject_hours[subject] = weight
        total_weight += weight
    
    # 分配时间
    available_hours = request.study_hours_per_day - 1  # 预留1小时休息
    for subject in subjects:
        base_hours = (subject_hours[subject] / total_weight) * available_hours
        subject_hours[subject] = round(max(1, min(base_hours, 4)), 1)
    
    # 生成各阶段计划
    phases = []
    week_counter = 1
    
    for phase_data in phases_data:
        weeks_in_phase = max(1, phase_data["duration_days"] // 7)
        weekly_plans = []
        
        for w in range(weeks_in_phase):
            week_subjects = []
            for subject in subjects:
                # 根据阶段调整时长
                if phase_data["name"] == "冲刺阶段":
                    if subject == "政治":
                        hours = min(subject_hours[subject] + 1, 4)
                    else:
                        hours = max(subject_hours[subject] - 0.5, 1)
                else:
                    hours = subject_hours[subject]
                
                tasks = _generate_weekly_tasks(
                    subject,
                    phase_data["name"],
                    w,
                    subject in weak_set
                )
                
                week_subjects.append(SubjectPlan(
                    subject=subject,
                    daily_hours=hours,
                    tasks=tasks
                ))
            
            # 生成周测和里程碑
            if phase_data["name"] == "基础阶段":
                weekly_test = f"第{w+1}周基础测试"
                milestone = "完成基础知识点学习"
            elif phase_data["name"] == "强化阶段":
                weekly_test = f"第{w+1}周强化测试"
                milestone = "重点知识突破"
            else:
                weekly_test = f"第{w+1}周模拟考试"
                milestone = "模拟实战训练"
            
            weekly_plans.append(WeeklyPlan(
                week=week_counter,
                subjects=week_subjects,
                weekly_test=weekly_test,
                milestone=milestone
            ))
            week_counter += 1
        
        phases.append(Phase(
            name=phase_data["name"],
            duration_days=phase_data["duration_days"],
            weekly_plan=weekly_plans,
            goals=[phase_data["description"], "保质保量完成每日任务", "及时复习巩固"]
        ))
    
    # 生成每日时间安排
    daily_schedule = DailySchedule(
        morning="08:00-12:00 数学/专业课（高难度科目）",
        afternoon="14:00-18:00 英语/政治（中等难度科目）",
        evening="19:00-21:00 复习巩固 + 错题整理"
    )
    
    # 生成备考建议
    tips = [
        "保持规律作息，每天保证7-8小时睡眠",
        "每周至少安排1天休息，避免疲劳备考",
        "建立错题本，定期回顾薄弱知识点",
        "多做真题，熟悉考试题型和时间分配",
        f"目标院校：{request.target_school}，目标专业：{request.target_major}",
        f"从当前{request.current_score}分提升至{request.target_score}分，需要{total_days}天系统备考"
    ]
    
    # 生成AI总结
    ai_summary = f"""
📚 智能学习计划总结

🎯 备考目标
- 目标院校：{request.target_school}
- 目标专业：{request.target_major}
- 目标分数：{request.target_score}分（当前预估：{request.current_score}分）

📅 备考时间
- 考试日期：{request.exam_date}
- 备考天数：{total_days}天
- 每日学习：{request.study_hours_per_day}小时

📊 阶段规划
1. 基础阶段（{phases_data[0]['duration_days']}天）：系统学习，打牢基础
2. 强化阶段（{phases_data[1]['duration_days']}天）：重点突破，查漏补缺
3. 冲刺阶段（{phases_data[2]['duration_days']}天）：模拟实战，调整状态

💡 薄弱科目：{', '.join(request.weak_subjects) if request.weak_subjects else '无'}

祝你备考顺利，金榜题名！🎓
""".strip()
    
    return GeneratePlanResponse(
        total_days=total_days,
        target_school=request.target_school,
        target_major=request.target_major,
        current_score=request.current_score,
        target_score=request.target_score,
        phases=phases,
        daily_schedule=daily_schedule,
        tips=tips,
        ai_summary=ai_summary
    )


# ============ API Endpoints ============
@router.post("/generate", response_model=GeneratePlanResponse)
async def generate_plan(
    request: GeneratePlanRequest,
    user: User = Depends(get_current_user),
):
    """AI 生成个性化学习计划"""
    return _generate_plan(request)


@router.post("/save", status_code=status.HTTP_201_CREATED)
async def save_plan(
    body: SavePlanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存学习计划到数据库"""
    try:
        # 将生成的计划转换为字符串存储
        plan_data_str = str(body.generated_plan)

        plan = StudyPlan(
            user_id=user.id,
            title=f"{body.plan_data.target_school} {body.plan_data.target_major} 备考计划",
            start_date=datetime.now().strftime("%Y-%m-%d"),
            end_date=body.plan_data.exam_date,
            subjects=body.plan_data.weak_subjects + ["数学", "英语", "专业课"],
            completed=False,
            progress=0
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {"id": str(plan.id), "message": "计划保存成功"}
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        db.rollback()
        logger.exception("保存学习计划失败: %s", e)
        raise HTTPException(status_code=500, detail="保存计划失败，请稍后重试")


@router.get("/mine")
async def get_my_plans(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户保存的学习计划"""
    plans = db.query(StudyPlan).filter(StudyPlan.user_id == user.id).all()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "subjects": p.subjects,
            "progress": p.progress,
            "completed": p.completed,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.get("/{plan_id}/progress")
async def get_plan_progress(
    plan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取学习计划进度跟踪"""
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == user.id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    # 计算进度信息
    start = datetime.strptime(plan.start_date, "%Y-%m-%d") if plan.start_date else None
    end = datetime.strptime(plan.end_date, "%Y-%m-%d") if plan.end_date else None
    now = datetime.now()
    
    total_days = (end - start).days if start and end else 0
    elapsed_days = (now - start).days if start else 0
    remaining_days = (end - now).days if end else 0
    
    return {
        "plan_id": str(plan.id),
        "title": plan.title,
        "progress": plan.progress,
        "total_days": total_days,
        "elapsed_days": max(0, elapsed_days),
        "remaining_days": max(0, remaining_days),
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "is_on_track": plan.progress >= (elapsed_days / total_days * 100) if total_days > 0 else False,
    }


@router.put("/{plan_id}/progress")
async def update_plan_progress(
    plan_id: UUID,
    body: ProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新学习计划进度"""
    try:
        plan = db.query(StudyPlan).filter(
            StudyPlan.id == plan_id,
            StudyPlan.user_id == user.id
        ).first()

        if not plan:
            raise HTTPException(status_code=404, detail="学习计划不存在")

        # 简单进度更新逻辑（实际项目中可以更复杂）
        plan.progress = min(100, plan.progress + 10)
        if plan.progress >= 100:
            plan.completed = True

        db.commit()

        return {"progress": plan.progress, "completed": plan.completed}
    except HTTPException:
        raise
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        db.rollback()
        logger.exception("更新学习计划进度失败: %s", e)
        raise HTTPException(status_code=500, detail="更新进度失败，请稍后重试")
