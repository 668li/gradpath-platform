"""7天微行动服务层 — 生成 7 天探索任务、生成洞察与自我发现报告。

核心哲学：不替用户决定，而是让用户通过 7 天低成本行动自己发现答案。
- 每天一个具体任务（调研/访谈/实践/复盘），15-30 分钟可完成
- 第 7 天生成"自我发现报告"
- LLM 可选，未配置时使用模板兜底
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.micro_action import MicroActionPlan, MicroActionTask
from app.services.ai_orchestrator import AIOrchestrator
from app.services.ai_service import AIServiceNotConfigured

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 7 天任务模板 — 根据目标路径定制
# 每条路径有 7 天的具体任务，task_type 取自 {research, interview, practice, reflect}
# ----------------------------------------------------------------------
TASK_BLUEPRINTS: dict[str, list[dict]] = {
    "kaoyan": [
        {
            "day": 1,
            "type": "research",
            "title": "调研 3 所目标院校",
            "desc": (
                "查找 3 所你心仪院校的招生简章与专业目录，记录："
                "复试线、报录比、考试科目、参考书目。"
                "提示：研招网、学校研究生院官网、学院通知栏是核心信息源。"
            ),
            "minutes": 25,
        },
        {
            "day": 2,
            "type": "research",
            "title": "找 2 篇「考研真实一天」",
            "desc": (
                "在知乎/B站/小红书搜「[目标专业] 考研一天」，阅读 2 篇内容，"
                "记录让你印象最深的一个细节（作息/压力/收获），并问自己："
                "「这种生活我能持续半年吗？」"
            ),
            "minutes": 20,
        },
        {
            "day": 3,
            "type": "interview",
            "title": "联系 1 位已上岸学长学姐",
            "desc": (
                "通过学院群/学长学姐群/小红书私信，联系 1 位目标院校已上岸的同学，"
                "问 3 个问题：备考最大的坑是什么？导师风格如何？现在回看会做什么 differently？"
            ),
            "minutes": 30,
        },
        {
            "day": 4,
            "type": "practice",
            "title": "做 1 套真题片段",
            "desc": (
                "找 1 套目标院校近 3 年真题，只做其中一道大题（约 30 分钟量），"
                "不要看答案。做完后对照答案给自己打分，记录「能上手」还是「完全懵」。"
            ),
            "minutes": 30,
        },
        {
            "day": 5,
            "type": "practice",
            "title": "读 1 篇目标导师论文摘要",
            "desc": (
                "在知网搜目标院校 1 位导师近 1 年的论文，只读摘要与引言。"
                "记录：你看懂多少？是否感兴趣？能不能用一句话复述研究问题？"
            ),
            "minutes": 20,
        },
        {
            "day": 6,
            "type": "reflect",
            "title": "写下这周的发现与感受",
            "desc": (
                "回答 3 个问题：① 这周最让我兴奋的瞬间是什么？"
                "② 最让我抗拒的瞬间是什么？③ 如果决定考研，"
                "我会想念现在生活的什么？"
            ),
            "minutes": 20,
        },
        {
            "day": 7,
            "type": "reflect",
            "title": "生成自我发现报告",
            "desc": (
                "回顾前 6 天的记录，系统将为你生成「自我发现报告」，"
                "包含你发现的喜好、你发现的挑战、建议的下一步。"
            ),
            "minutes": 15,
        },
    ],
    "employment": [
        {
            "day": 1,
            "type": "research",
            "title": "查 3 个目标 JD",
            "desc": (
                "在 BOSS/拉勾/牛客搜 3 个目标岗位的 JD，记录："
                "核心技能词出现频率 Top 5、薪资区间、学历/经验门槛。"
                "提示：JD 是岗位最真实的「需求清单」。"
            ),
            "minutes": 20,
        },
        {
            "day": 2,
            "type": "research",
            "title": "看 2 个「目标岗位一天」Vlog",
            "desc": (
                "在 B站/小红书搜「[岗位名] 一天」，看 2 个视频，"
                "记录让你最意外的 1 个细节，问自己："
                "「如果这就是我未来 3 年，我能接受吗？」"
            ),
            "minutes": 20,
        },
        {
            "day": 3,
            "type": "interview",
            "title": "约 1 位从业者喝咖啡/线上聊",
            "desc": (
                "通过校友/LinkedIn/脉脉联系 1 位目标岗位从业者，"
                "聊 20 分钟，问 3 个问题：① 入行最关键的 1 个能力？"
                "② 这行最不喜欢的一面？③ 1 年新人典型一周长什么样？"
            ),
            "minutes": 30,
        },
        {
            "day": 4,
            "type": "practice",
            "title": "完成 1 个岗位小项目",
            "desc": (
                "选 1 个 JD 中提到的高频技能，做 1 个 2-4 小时的小作品"
                "（如写 1 个 API、做 1 张数据看板、写 1 篇产品分析）。"
                "不求完美，只求「能 demo」。"
            ),
            "minutes": 30,
        },
        {
            "day": 5,
            "type": "practice",
            "title": "写一版 1 页简历",
            "desc": (
                "用 Notion/语雀写一版 1 页简历，把昨天的项目成果放进去。"
                "重点不是排版，是回答：JD 关键词我命中了几个？缺什么？"
            ),
            "minutes": 25,
        },
        {
            "day": 6,
            "type": "reflect",
            "title": "记录这周的发现与感受",
            "desc": (
                "回答 3 个问题：① 做这个岗位的小项目时，我什么时候进入心流？"
                "② 什么时候想放弃？③ 如果不选这条路径，"
                "我最舍不得的是什么？"
            ),
            "minutes": 20,
        },
        {
            "day": 7,
            "type": "reflect",
            "title": "生成自我发现报告",
            "desc": ("回顾前 6 天的记录，系统将为你生成「自我发现报告」。"),
            "minutes": 15,
        },
    ],
    "civil_service": [
        {
            "day": 1,
            "type": "research",
            "title": "查 3 个目标岗位的招录信息",
            "desc": (
                "在公考雷达/华图/中公搜 3 个目标岗位，记录："
                "报录比、进面分数线、专业/政治面貌/户籍限制。"
                "提示：「萝卜岗」常藏在专业限制与备注里。"
            ),
            "minutes": 25,
        },
        {
            "day": 2,
            "type": "research",
            "title": "看 2 篇「上岸真实一天」",
            "desc": (
                "在知乎/小红书搜「[岗位名] 真实一天」，读 2 篇内容，"
                "记录最让你意外的 1 个细节（工作内容/加班/人情）。"
                "问自己：这种节奏我能持续 5 年吗？"
            ),
            "minutes": 20,
        },
        {
            "day": 3,
            "type": "interview",
            "title": "联系 1 位上岸前辈",
            "desc": (
                "通过校友/亲友/小红书私信联系 1 位目标岗位上岸前辈，"
                "问 3 个问题：① 备考最关键的 1 个月做了什么？"
                "② 入职后最大的落差？③ 给应届生 1 条建议？"
            ),
            "minutes": 30,
        },
        {
            "day": 4,
            "type": "practice",
            "title": "做 1 套行测片段",
            "desc": (
                "找 1 套近 3 年真题，只做言语理解或数量关系的 1 个模块"
                "（约 30 分钟量），不看答案做完后对答案。"
                "记录：能上手还是完全懵？做题时的感受是紧张还是兴奋？"
            ),
            "minutes": 30,
        },
        {
            "day": 5,
            "type": "practice",
            "title": "写 1 段申论开头",
            "desc": (
                "选 1 道近 3 年申论真题，只写开头 200 字。"
                "写完后对照优秀范文，记录：我的立意/素材/语言差距在哪？"
            ),
            "minutes": 25,
        },
        {
            "day": 6,
            "type": "reflect",
            "title": "记录这周的发现与感受",
            "desc": (
                "回答 3 个问题：① 做行测/申论时，我最享受哪类题？"
                "② 看完真实一天，我对这个职业的想象有什么变化？"
                "③ 如果不考公，我会不会后悔？"
            ),
            "minutes": 20,
        },
        {
            "day": 7,
            "type": "reflect",
            "title": "生成自我发现报告",
            "desc": ("回顾前 6 天的记录，系统将为你生成「自我发现报告」。"),
            "minutes": 15,
        },
    ],
}

# 未知路径兜底为 employment
_FALLBACK_PATH = "employment"


def _get_blueprint(target_path: str) -> list[dict]:
    """获取指定路径的任务模板，未知路径兜底为 employment。"""
    bp = TASK_BLUEPRINTS.get(target_path)
    if bp is None:
        bp = TASK_BLUEPRINTS[_FALLBACK_PATH]
    return bp


# ----------------------------------------------------------------------
# 服务函数
# ----------------------------------------------------------------------
def create_plan(
    db: Session, user_id: UUID, target_path: str, target_role: str | None = None
) -> MicroActionPlan:
    """创建 7 天微行动计划并生成 7 个任务。

    如果用户已有 active plan，先把旧 plan 标记为 abandoned 再创建新的，
    避免同时存在多个活跃计划。
    """
    # 关闭用户已有的 active 计划
    existing = (
        db.query(MicroActionPlan)
        .filter(
            MicroActionPlan.user_id == user_id,
            MicroActionPlan.status == "active",
        )
        .all()
    )
    for plan in existing:
        plan.status = "abandoned"

    blueprint = _get_blueprint(target_path)
    plan = MicroActionPlan(
        user_id=user_id,
        target_path=target_path,
        target_role=target_role,
        status="active",
    )
    db.add(plan)
    db.flush()  # 取得 plan.id

    tasks = [
        MicroActionTask(
            plan_id=plan.id,
            day_number=item["day"],
            task_type=item["type"],
            title=item["title"],
            description=item["desc"],
            estimated_minutes=item["minutes"],
            status="pending",
        )
        for item in blueprint
    ]
    db.add_all(tasks)
    db.commit()
    db.refresh(plan)
    return plan


def get_plan(db: Session, plan_id: UUID) -> MicroActionPlan | None:
    return db.query(MicroActionPlan).filter(MicroActionPlan.id == plan_id).first()


def get_current_plan(db: Session, user_id: UUID) -> MicroActionPlan | None:
    """获取用户当前活跃 plan（按时间倒序取最新）。"""
    return (
        db.query(MicroActionPlan)
        .filter(
            MicroActionPlan.user_id == user_id,
            MicroActionPlan.status == "active",
        )
        .order_by(MicroActionPlan.created_at.desc())
        .first()
    )


def get_history(db: Session, user_id: UUID, limit: int = 20) -> list[MicroActionPlan]:
    """获取用户所有 plan 历史（按时间倒序）。"""
    return (
        db.query(MicroActionPlan)
        .filter(MicroActionPlan.user_id == user_id)
        .order_by(MicroActionPlan.created_at.desc())
        .limit(limit)
        .all()
    )


def get_task(db: Session, task_id: UUID) -> MicroActionTask | None:
    return db.query(MicroActionTask).filter(MicroActionTask.id == task_id).first()


def _calculate_progress(tasks: list[MicroActionTask]) -> int:
    """计算进度 = 完成任务数 / 7 * 100（completed 与 skipped 都算「已处理」）。"""
    done = sum(1 for t in tasks if t.status in ("completed", "skipped"))
    return int(done / len(tasks) * 100) if tasks else 0


def _check_plan_completion(db: Session, plan: MicroActionPlan) -> None:
    """检查 plan 是否 7 天全部处理完毕（completed 或 skipped），是则更新状态。"""
    tasks = db.query(MicroActionTask).filter(MicroActionTask.plan_id == plan.id).all()
    if not tasks:
        return
    all_done = all(t.status in ("completed", "skipped") for t in tasks)
    if all_done and plan.status != "completed":
        plan.status = "completed"
        plan.completed_at = datetime.now(timezone.utc)
        db.commit()


async def complete_task(db: Session, task_id: UUID, user_response: str) -> MicroActionTask:
    """完成任务：标记完成 + 生成洞察 + 检查 plan 是否完成。"""
    task = get_task(db, task_id)
    if task is None:
        raise ValueError("任务不存在")

    # 幂等守卫：重复调用不重复加经验、不重复生成洞察
    if task.status == "completed":
        return task

    user_response = (user_response or "").strip()

    task.status = "completed"
    task.user_response = user_response
    task.completed_at = datetime.now(timezone.utc)

    # 写穿全局连击账本（P0-2）——真实完成微行动才计入 StreakRecord
    plan = get_plan(db, task.plan_id)
    if plan is not None:
        from app.services.streak_service import record_activity

        record_activity(
            db,
            plan.user_id,
            "micro",
            xp=3,
            action_detail=f"微行动 Day {task.day_number}: {task.title}",
        )

    # 尝试生成 AI 洞察，无 LLM key 时使用模板兜底
    insight = await _generate_insight(task)
    task.insight = insight

    db.commit()
    db.refresh(task)

    # 检查 plan 是否完成
    if plan:
        _check_plan_completion(db, plan)

    return task


def skip_task(db: Session, task_id: UUID) -> MicroActionTask:
    """跳过任务：仅标记状态，不要求 user_response。"""
    task = get_task(db, task_id)
    if task is None:
        raise ValueError("任务不存在")

    # 幂等守卫：已完成/已跳过的任务不再改状态（complete 后误调 skip 不得覆盖）
    if task.status in ("completed", "skipped"):
        return task

    task.status = "skipped"
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)

    # 检查 plan 是否完成
    plan = get_plan(db, task.plan_id)
    if plan:
        _check_plan_completion(db, plan)

    return task


# ----------------------------------------------------------------------
# AI 洞察与自我发现报告
# ----------------------------------------------------------------------
INSIGHT_SYSTEM_PROMPT = """你是一位职业探索教练，擅长从用户简短的行动记录中提炼洞察。

用户刚完成了一项 7 天微行动任务。请基于任务描述与用户记录，给出一段 80-150 字的洞察，
要求：
1. 用「从你的记录中，我发现...」开头
2. 指出用户记录中透露的一个具体信号（情绪/兴趣/抗拒）
3. 给出一个轻量的下一步建议（不要替用户做决定）
4. 语气温暖、不带评判

不要使用 markdown 格式，直接输出自然语言段落。"""


REPORT_SYSTEM_PROMPT = """你是一位职业探索教练，正在为用户生成 7 天微行动的「自我发现报告」。

请基于用户 7 天的行动记录，生成一份结构化报告，包含以下 3 部分：

【你发现的喜好】
- 从用户的记录中提炼出他/她明显感兴趣、享受、愿意投入的方面（2-3 条）

【你发现的挑战】
- 从用户的记录中提炼出他/她遇到的、抗拒的、感到困难的方面（2-3 条）

【建议的下一步】
- 基于「不替用户决定」的原则，给出 2-3 个可执行的下一步探索方向
- 每个方向应是一条具体动作（不是结论），如「再花 1 周深入了解 X」「找 1 位 Y 从业者聊」

请用中文输出，语气温暖但有建设性，避免任何「你应该」「你必须」类表述。"""


async def _generate_insight(task: MicroActionTask) -> str:
    """为单个任务生成 AI 洞察，无 LLM key 时使用模板兜底。"""
    try:
        orchestrator = AIOrchestrator()
        user_prompt = (
            f"【任务】第 {task.day_number} 天 · {task.title}\n"
            f"【任务描述】{task.description}\n"
            f"【用户记录】{task.user_response or '(用户未填写)'}"
        )
        raw = await orchestrator.chat(
            system_prompt=INSIGHT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            timeout=30,
        )
        return raw
    except (AIServiceNotConfigured, Exception) as e:
        logger.info("AI 洞察生成降级到模板: %s", e)
        return _template_insight(task)


def _template_insight(task: MicroActionTask) -> str:
    """无 LLM 时的洞察模板。"""
    return (
        f"从你的记录中，我发现你在第 {task.day_number} 天的行动里留下了具体的痕迹。"
        "你愿意花 15-30 分钟去验证一个想法，这本身就是低成本的探索。"
        "下一步可以带着这次记录里的具体感受，继续观察自己在不同任务上的投入度差异。"
    )


async def generate_self_discovery_report(db: Session, plan_id: UUID) -> str:
    """第 7 天生成自我发现报告：汇总 7 天用户响应，输出喜好/挑战/下一步。"""
    plan = get_plan(db, plan_id)
    if plan is None:
        raise ValueError("计划不存在")

    tasks = (
        db.query(MicroActionTask)
        .filter(MicroActionTask.plan_id == plan_id)
        .order_by(MicroActionTask.day_number)
        .all()
    )

    # 优先尝试 LLM 生成
    try:
        orchestrator = AIOrchestrator()
        records_lines = [
            f"目标路径：{plan.target_path}"
            + (f"（{plan.target_role}）" if plan.target_role else "")
        ]
        for t in tasks:
            status_label = "完成" if t.status == "completed" else "跳过"
            records_lines.append(f"\nDay {t.day_number} · {t.title} [{status_label}]")
            if t.user_response:
                records_lines.append(f"用户记录：{t.user_response}")
        user_prompt = "\n".join(records_lines)

        report = await orchestrator.chat(
            system_prompt=REPORT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            timeout=40,
        )
    except (AIServiceNotConfigured, Exception) as e:
        logger.info("自我发现报告降级到模板: %s", e)
        report = _template_self_discovery_report(plan, tasks)

    plan.self_discovery_report = report
    db.commit()
    return report


def _template_self_discovery_report(plan: MicroActionPlan, tasks: list[MicroActionTask]) -> str:
    """无 LLM 时的自我发现报告模板。"""
    completed = [t for t in tasks if t.status == "completed"]
    skipped = [t for t in tasks if t.status == "skipped"]
    target_desc = plan.target_path + (f"（{plan.target_role}）" if plan.target_role else "")

    return (
        f"【自我发现报告】\n\n"
        f"目标路径：{target_desc}\n"
        f"完成 {len(completed)} / 7 项任务，跳过 {len(skipped)} 项\n\n"
        "【你发现的喜好】\n"
        "- 在完成度高的任务里，你能够持续投入 15-30 分钟，"
        "说明这条路径至少在某些环节与你的节奏契合。\n"
        "- 你愿意主动记录而非仅浏览，这是一种「带判断的行动」倾向。\n\n"
        "【你发现的挑战】\n"
        f"- 跳过了 {len(skipped)} 项任务，可以问问自己是任务本身难，"
        "还是触发了某种回避情绪。\n"
        "- 7 天不足以看清一条路径，但它能帮你看清自己当下的能量分布。\n\n"
        "【建议的下一步】\n"
        "- 再花 1 周时间，针对最让你有触感的 1 个任务做深度延伸（如再读 1 篇论文、再做 1 个项目）。\n"
        "- 找 1 位不同路径的从业者聊一聊，对比两次访谈的感受差异。\n"
        "- 不急于下结论，把这份报告与 1 个月后自己的状态做对比。"
    )


__all__ = [
    "create_plan",
    "get_plan",
    "get_current_plan",
    "get_history",
    "get_task",
    "complete_task",
    "skip_task",
    "generate_self_discovery_report",
]
