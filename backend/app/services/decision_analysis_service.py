"""决策分析服务层 — 预验尸 + 决策矩阵 + 红队质疑。

在决策前就预想失败（Pre-mortem），用加权矩阵量化选项，
用红队问题检验假设。真正提升决策质量。
"""
import json
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.decision_analysis import DecisionAnalysis
from app.services.ai_service import AIService
from app.services.ai_orchestrator import AIOrchestrator


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
            weighted_results.append({
                "option": option_name,
                "total_score": round(total, 2),
            })
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
            breakdown.append({"criterion": cname, "weight": weight, "score": score, "weighted": round(weighted, 2)})
        results.append({
            "option": option_name,
            "total_score": round(total, 2),
            "breakdown": breakdown,
        })
    results.sort(key=lambda x: x["total_score"], reverse=True)
    winner = results[0]["option"] if results else None
    return {"results": results, "winner": winner}


async def analyze_premortem(title: str, options: list[str], reasons: list[str]) -> dict:
    """AI 分析预验尸结果：聚类风险 + 生成保障措施。"""
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

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, TypeError):
                return {"categories": []}
        else:
            return {"categories": []}

    return data


async def generate_red_team_questions(title: str, options: list[str], reasoning: str | None) -> list[str]:
    """AI 生成红队质疑问题。"""
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

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)

    questions = [q.strip().lstrip("0123456789.、）) ") for q in raw.strip().split("\n") if q.strip()]
    return questions[:7]


async def generate_ai_analysis(db: Session, analysis_id: UUID) -> str:
    """AI 综合分析决策（预验尸 + 矩阵 + 红队）。"""
    analysis = db.query(DecisionAnalysis).filter(DecisionAnalysis.id == analysis_id).first()
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
