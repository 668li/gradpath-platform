"""决策分析服务层 — 预验尸 + 决策矩阵 + 红队质疑。

在决策前就预想失败（Pre-mortem），用加权矩阵量化选项，
用红队问题检验假设。真正提升决策质量。
"""

import json
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.decision_analysis import DecisionAnalysis
from app.services.ai_orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)


def create_analysis(db: Session, user_id: UUID, data: dict) -> DecisionAnalysis:
    """创建决策分析。自动计算矩阵加权得分。"""
    criteria = data.get("criteria", [])
    matrix_scores = data.get("matrix_scores", [])

    # 计算加权得分
    weighted_results = []
    winner = None
    if criteria and matrix_scores:
        for option_data in matrix_scores:
            option_name = option_data.get("name", option_data.get("option", ""))
            scores = option_data.get("scores", {})
            total = 0
            for c in criteria:
                cname = c.get("criterion", "")
                weight = c.get("weight", 0)
                score = scores.get(cname, 0)
                total += weight * score / 100
            weighted_results.append(
                {
                    "option": option_name,
                    "total_score": round(total, 2),
                }
            )
        if weighted_results:
            winner = max(weighted_results, key=lambda x: x["total_score"])["option"]

    analysis = DecisionAnalysis(
        user_id=user_id,
        decision_id=data.get("decision_id"),
        title=data["title"],
        options=data.get("options", []),
        premortem_reasons=data.get("premortem_reasons", []),
        premortem_categories=data.get("premortem_categories", []),
        safeguards=data.get("safeguards", []),
        criteria=criteria,
        matrix_scores=matrix_scores,
        weighted_results=weighted_results,
        winner=winner,
        red_team_questions=data.get("red_team_questions", []),
        red_team_answers=data.get("red_team_answers", []),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def get_analyses(db: Session, user_id: UUID) -> list[DecisionAnalysis]:
    return (
        db.query(DecisionAnalysis)
        .filter(DecisionAnalysis.user_id == user_id)
        .order_by(DecisionAnalysis.created_at.desc())
        .all()
    )


def get_analysis(db: Session, user_id: UUID, analysis_id: UUID) -> DecisionAnalysis | None:
    return (
        db.query(DecisionAnalysis)
        .filter(DecisionAnalysis.id == analysis_id, DecisionAnalysis.user_id == user_id)
        .first()
    )


def compute_matrix(criteria: list[dict], matrix_scores: list[dict]) -> dict:
    """计算决策矩阵加权得分（不保存，仅返回结果）。"""
    results = []
    for option_data in matrix_scores:
        option_name = option_data.get("name", "")
        scores = option_data.get("scores", {})
        total = 0
        breakdown = []
        for c in criteria:
            cname = c.get("criterion", "")
            weight = c.get("weight", 0)
            score = scores.get(cname, 0)
            weighted = weight * score / 100
            total += weighted
            breakdown.append(
                {
                    "criterion": cname,
                    "weight": weight,
                    "score": score,
                    "weighted": round(weighted, 2),
                }
            )
        results.append(
            {
                "option": option_name,
                "total_score": round(total, 2),
                "breakdown": breakdown,
            }
        )
    results.sort(key=lambda x: x["total_score"], reverse=True)
    winner = results[0]["option"] if results else None
    return {"results": results, "winner": winner}


# 风险关键词 → (类别名, 保障措施) — 零 LLM 兜底聚类的规则表
_RISK_KEYWORDS: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("时间", "拖延", "来不及", "进度", "备考", "复习", "工期"),
        "时间与执行力风险",
        "把大目标拆成周级里程碑，每周日固定复盘一次，落后两周即启动计划调整。",
    ),
    (
        ("钱", "经济", "费用", "收入", "预算", "存款", "负债"),
        "经济压力风险",
        "预先备足 6-12 个月的生活与学习预算，写下最小可承受开支线并告知家人。",
    ),
    (
        ("竞争", "报录", "名额", "内卷", "对手", "分数线", "招录"),
        "竞争烈度风险",
        "报名前核对近三年报录比与分数线趋势，并准备一档更稳的备选方案。",
    ),
    (
        ("家人", "家庭", "父母", "对象", "感情", "婚姻"),
        "家庭与关系风险",
        "带着数据和折中方案与家人做一次正式沟通，明确底线与支持条件。",
    ),
    (
        ("健康", "身体", "心态", "焦虑", "失眠", "情绪", "压力"),
        "身心健康风险",
        "每周保留固定休息与运动时间，设置心态预警信号与求助渠道。",
    ),
    (
        ("信息", "不确定", "变化", "政策", "市场", "行业", "裁员", "形势"),
        "外部不确定性风险",
        "为关键假设设定验证时间点，每月核查一次外部信号，偏离即重估。",
    ),
    (
        ("能力", "基础", "学不会", "底子", "跨考", "转行", "经验"),
        "能力与基础风险",
        "先做一次摸底测试定位真实差距，把补基础列入前 30 天计划。",
    ),
]
_DEFAULT_RISK = (
    "综合执行风险",
    "把最可能失败的 1-2 个环节写成书面预案，明确触发条件与替代动作。",
)


def _template_premortem(reasons: list[str]) -> dict:
    """零 LLM 的预验尸模板兜底 — 按关键词把用户原因聚类为 3-5 类风险 + 通用保障措施。

    返回结构与前端契约一致：categories[].category/.reasons + safeguards[].category/.action。
    """
    categories: list[dict] = []
    by_name: dict[str, dict] = {}
    unmatched: list[str] = []
    seen: set[str] = set()

    for reason in reasons:
        text = str(reason).strip()
        if not text or text in seen:  # 去重
            continue
        seen.add(text)
        for keywords, name, safeguard in _RISK_KEYWORDS:
            if any(k in text for k in keywords):
                bucket = by_name.get(name)
                if bucket is None:
                    bucket = {"category": name, "reasons": [], "_safeguard": safeguard}
                    by_name[name] = bucket
                    categories.append(bucket)
                bucket["reasons"].append(text)
                break
        else:
            unmatched.append(text)

    if unmatched:
        name, safeguard = _DEFAULT_RISK
        bucket = by_name.get(name)
        if bucket is None:
            bucket = {"category": name, "reasons": [], "_safeguard": safeguard}
            by_name[name] = bucket
            categories.append(bucket)
        bucket["reasons"].extend(unmatched[:20])

    # 至少一类，至多五类（超出时保留最具体的靠前类别）
    if not categories:
        name, safeguard = _DEFAULT_RISK
        categories.append({"category": name, "reasons": [], "_safeguard": safeguard})
    categories = categories[:5]

    safeguards = [{"category": c["category"], "action": c["_safeguard"]} for c in categories]
    return {
        "categories": [{"category": c["category"], "reasons": c["reasons"]} for c in categories],
        "safeguards": safeguards,
    }


async def analyze_premortem(title: str, options: list[str], reasons: list[str]) -> dict:
    """AI 分析预验尸结果：聚类风险 + 生成保障措施。

    LLM 不可用/返回不可解析时降级为模板聚类（ai_used=False），绝不裸 500。
    返回结构对齐前端契约：{ categories: [{category, reasons}], safeguards: [{category, action}], ai_used }。
    """
    system_prompt = """你是一位风险管理专家。用户做了一个决策预验尸：假设决策失败了，列出了可能的原因。

请将原因聚类为 3-5 个风险类别，并为每个类别生成一个保障措施。

严格输出 JSON：
{
  "categories": [
    {
      "name": "风险类别名",
      "reasons": ["归类到此类的原因"],
      "safeguard": "针对此类风险的保障措施"
    }
  ]
}
不要输出 JSON 以外的内容。"""

    context = f"""决策标题：{title}
选项：{', '.join(options)}
预验尸原因：
"""
    for i, r in enumerate(reasons, 1):
        context += f"{i}. {r}\n"

    template_result = _template_premortem(reasons)

    try:
        orchestrator = AIOrchestrator()
        raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)
    except Exception as exc:
        logger.warning("预验尸 AI 分析降级为模板聚类（ai_used=False）: %s", exc)
        return {**template_result, "ai_used": False}

    data = None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, TypeError):
                data = None

    raw_categories = data.get("categories") if isinstance(data, dict) else None
    categories: list[dict] = []
    safeguards: list[dict] = []
    if isinstance(raw_categories, list):
        for c in raw_categories:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or c.get("category") or "").strip()
            if not name:
                continue
            reason_list = [str(r).strip() for r in (c.get("reasons") or []) if str(r).strip()]
            categories.append({"category": name, "reasons": reason_list or [name]})
            action = str(c.get("safeguard") or c.get("action") or "").strip()
            if action:
                safeguards.append({"category": name, "action": action})

    if not categories:
        # LLM 返回不可解析 → 诚实降级为模板聚类
        logger.warning("预验尸 AI 返回不可解析，降级为模板聚类（ai_used=False）")
        return {**template_result, "ai_used": False}

    return {"categories": categories, "safeguards": safeguards, "ai_used": True}


def _heuristic_red_team_questions(
    title: str, options: list[str], reasoning: str | None
) -> list[str]:
    """规则化红队问题 — 零 LLM 的决策科学启发式，LLM 不可用时的诚实降级。

    框架与 LLM prompt 同源（未验证前提/替代论证/二阶效应/安静成本/可逆性），
    问题嵌入用户自己的选项文本，保证针对性而非泛泛清单。
    """
    a = options[0] if options else "当前选项"
    b = options[1] if len(options) > 1 else "另一个选项"
    more = options[2:] if len(options) > 2 else []
    more_text = f"（还有 {'、'.join(more)}）" if more else ""
    return [
        "这个决定最依赖哪个假设？如果该假设在半年后被证伪，你会如何发现？",
        f"支持「{b}」的最强论据是什么？请用自己的话说出来，说不出来说明你还没认真考虑过它。",
        f"如果选了「{a}」，6 个月后你的日常状态会有什么具体不同？{more_text}",
        f"选择「{a}」要放弃什么安静成本（时间、注意力、机会）？你为它们标过价吗？",
        f"如果选错了，从「{a}」退回「{b}」的真实代价是什么？这个决定可逆吗？",
        "做这个决定前，你最缺的一条关键信息是什么？拿到它需要多少时间或金钱？",
        "和你条件相似、做过同样选择的人，结果如何？你真正了解几例（而不是只记得成功的）？",
    ]


async def generate_red_team_questions(
    title: str, options: list[str], reasoning: str | None
) -> list[str]:
    """AI 生成红队质疑问题；LLM 不可用/返回为空时降级到规则化问题（零 LLM 可跑）。"""
    system_prompt = """你是一位红队分析师，任务是质疑一个决策的薄弱假设。

请生成 7 个尖锐的红队质疑问题，覆盖：
- 被假设但未验证的前提
- 最强替代方案的论据
- 二阶效应（第一后果之后会发生什么）
- 安静成本（时间、注意力、机会成本）
- 可逆性与期权价值

每个问题一行，不要编号，不要额外说明。"""

    context = f"""决策标题：{title}
选项：{', '.join(options)}
决策理由：{reasoning or '未提供'}"""

    try:
        orchestrator = AIOrchestrator()
        raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)
        questions = [
            q.strip().lstrip("0123456789.、）) ") for q in raw.strip().split("\n") if q.strip()
        ]
    except Exception:
        questions = []
    if not questions:
        questions = _heuristic_red_team_questions(title, options, reasoning)
    return questions[:7]


async def generate_ai_analysis(db: Session, analysis_id: UUID, user_id: UUID | None = None) -> str:
    """AI 综合分析决策（预验尸 + 矩阵 + 红队）。"""
    query = db.query(DecisionAnalysis).filter(DecisionAnalysis.id == analysis_id)
    # 安全修复 H4: 验证分析属于请求用户，防止 IDOR 跨用户读取
    if user_id is not None:
        query = query.filter(DecisionAnalysis.user_id == user_id)
    analysis = query.first()
    if not analysis:
        raise ValueError("分析不存在")

    system_prompt = """你是一位决策分析教练。用户完成了完整的决策分析（预验尸+矩阵+红队）。

请给出综合分析和最终建议：
1. 矩阵结果是否可信？有没有被忽略的因素？
2. 预验尸揭示的最大风险是什么？保障措施够不够？
3. 红队质疑中哪个问题最值得深思？
4. 你的最终建议是什么？（继续/修改/暂停/换方向）

用中文，300-400 字，直接不客套。不使用 markdown。"""

    context = f"""决策标题：{analysis.title}
选项：{', '.join(analysis.options)}

决策矩阵结果：
"""
    for r in analysis.weighted_results:
        context += f"  - {r.get('option', '?')}: {r.get('total_score', 0)} 分\n"
    context += f"矩阵赢家：{analysis.winner or '未计算'}\n\n"

    context += "预验尸风险类别：\n"
    for r in analysis.premortem_reasons[:5]:
        if isinstance(r, dict):
            context += f"  - [{r.get('category', '?')}] {r.get('reason', '?')}\n"

    context += "\n保障措施：\n"
    for s in analysis.safeguards[:5]:
        if isinstance(s, dict):
            context += f"  - [{s.get('category', '?')}] {s.get('action', '?')}\n"

    context += "\n红队质疑（前3个）：\n"
    for q in analysis.red_team_questions[:3]:
        context += f"  - {q}\n"

    orchestrator = AIOrchestrator()
    result = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)
    analysis.ai_analysis = result
    db.commit()
    return result
