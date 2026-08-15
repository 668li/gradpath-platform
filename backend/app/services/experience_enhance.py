"""考研经验贴 LLM 结构化增强（Phase G 挂载点）。

对审核确认入库的 ExperiencePost 异步生成 ai_summary + category 修正 +
structured_meta 补全。规则版结果（quality_score/grade、structured_meta、
is_promotion 等）在 promote 落库时已计算，LLM 是可选增强：

- 失败/超时/未配置 LLM_API_KEY → 降级保留规则版结果，ai_summary 保持
  NULL（诚实，不伪造 AI 内容），前端回退展示 summary 字段
- 本轮默认不投递（LLM_API_KEY 为空）；配好 key 后 schedule_xxx 自动生效

与 news_enhance.py 模式一致，不 commit —— 由调用方统一提交。
"""
import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.experience_post import ExperiencePost

logger = logging.getLogger(__name__)

# 单条 LLM 调用超时（秒）— 超时即降级该条
LLM_TIMEOUT = 25
# LLM 输出摘要长度约束
SUMMARY_MAX_LEN = 160
# 有效经验贴分类（与 transformer.CATEGORY_RULES 键集一致，含 Phase H 新增维度）
VALID_CATEGORIES = {
    "general", "初试", "复试", "调剂", "择校", "复习", "备考", "心态", "避坑",
}

_SYSTEM_PROMPT = (
    "你是考研经验内容质量分析师。基于给定的考研经验贴标题与正文，输出严格 JSON（不要任何其他文字）："
    "{\"summary\": \"≤120字中文摘要，只提炼对备考者有行动价值的干货（时间规划、复习方法、院校选择要点、坑点），不编造原文没有的事实\", "
    "\"category\": \"经验贴分类，从以下取值：general/初试/复试/调剂/择校/复习/备考/心态/避坑\", "
    "\"structured_meta\": {\"subject\": \"学科，如数学/英语/政治/408/计算机，原文没有则为 null\", "
    "\"stage\": \"阶段，如择校/初试/复试/调剂/备考，原文没有则为 null\", "
    "\"school\": \"院校名，原文没有则为 null\", "
    "\"target_score\": \"目标分数整数，原文没有则为 null\"}}。"
    "所有字段只从原文提炼，原文没有的一律写 null，禁止编造。"
)


def _build_user_prompt(post: ExperiencePost) -> str:
    return (
        f"标题：{post.title}\n"
        f"现有分类：{post.category}\n"
        f"正文：{(post.content or '')[:2000]}"
    )


def _parse_llm_json(text: str) -> dict | None:
    """解析 LLM 返回的 JSON（容忍 markdown 代码块与前后缀噪音）。"""
    if not text:
        return None
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.S)
    if fence:
        cleaned = fence.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None


def _sanitize_meta(raw_meta: object) -> dict:
    """清洗 LLM 输出的 structured_meta（类型护栏，非法字段丢弃）。"""
    if not isinstance(raw_meta, dict):
        return {}
    cleaned: dict = {}
    for key, cast in (
        ("subject", str),
        ("stage", str),
        ("school", str),
    ):
        value = raw_meta.get(key)
        if isinstance(value, str) and value.strip():
            cleaned[key] = value.strip()[:50]
    target = raw_meta.get("target_score")
    if isinstance(target, (int, float)) and 100 <= int(target) <= 500:
        cleaned["target_score"] = int(target)
    return cleaned


def _rule_based_summary(post: ExperiencePost) -> str | None:
    """LLM 不可用时的规则兜底摘要：由结构化元信息生成确定性要点提示。"""
    meta = post.structured_meta or {}
    parts = []
    if meta.get("school"):
        parts.append(f"院校：{meta['school']}")
    if meta.get("subject"):
        parts.append(f"学科：{meta['subject']}")
    if meta.get("stage"):
        parts.append(f"阶段：{meta['stage']}")
    if meta.get("target_score"):
        parts.append(f"目标分：{meta['target_score']}")
    if meta.get("methods"):
        parts.append("方法：" + "/".join(meta["methods"][:3]))
    if parts:
        return "要点：" + "；".join(parts)
    return None


async def enhance_experience_item(db: Session, post: ExperiencePost) -> dict:
    """单条经验贴 LLM 增强（ai_summary + category 修正 + structured_meta 补全）。

    成功：回填 ai_summary/category/structured_meta。
    失败/超时/未配置：保留规则版结果，ai_summary 不动（诚实降级）。
    不 commit —— 由调用方（Celery 任务）统一提交。
    """
    try:
        from app.services.ai_orchestrator import AIOrchestrator

        ai = AIOrchestrator()
        raw = await ai.chat(
            _SYSTEM_PROMPT,
            _build_user_prompt(post),
            timeout=LLM_TIMEOUT,
        )
        parsed = _parse_llm_json(raw)
        if not parsed:
            logger.info("[experience_enhance] LLM 输出非 JSON，降级 %s", post.id)
            return {"status": "degraded", "reason": "invalid_llm_json"}

        summary = parsed.get("summary")
        if isinstance(summary, str) and summary.strip():
            post.ai_summary = summary.strip()[:SUMMARY_MAX_LEN]

        category = parsed.get("category")
        if isinstance(category, str) and category in VALID_CATEGORIES:
            post.category = category

        llm_meta = _sanitize_meta(parsed.get("structured_meta"))
        if llm_meta:
            # 合并而非覆盖：保留规则版已抽到的字段，LLM 只补缺失的
            merged = dict(post.structured_meta or {})
            for key, value in llm_meta.items():
                if not merged.get(key):
                    merged[key] = value
            post.structured_meta = merged

        logger.info(
            "[experience_enhance] 增强成功 %s (summary=%s, meta_keys=%s)",
            post.id, bool(post.ai_summary), sorted((post.structured_meta or {}).keys()),
        )
        return {"status": "enhanced", "meta_keys": sorted(llm_meta.keys())}
    except Exception as e:  # noqa: BLE001 — 降级模式：任何失败保留规则版结果
        logger.warning("[experience_enhance] LLM 增强失败降级 %s: %s", post.id, e)
        return {"status": "degraded", "reason": str(e)}


def schedule_experience_enhancement(limit: int = 5) -> bool:
    """投递批量增强任务到 Celery ai 队列（fire-and-forget）。

    broker 不可用（开发环境 memory://）时跳过；配好 LLM key 后启用。
    返回是否成功投递。
    """
    try:
        from app.celery_app import celery_app
        from app.config import settings

        if not settings.REDIS_URL or str(celery_app.conf.broker_url).startswith("memory://"):
            return False
        from app.tasks.ai_tasks import enhance_experience_post_batch

        enhance_experience_post_batch.delay(limit=limit)
        logger.info("[experience_enhance] 已投递批量增强任务 limit=%d", limit)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[experience_enhance] 投递增强任务失败（跳过）: %s", e)
        return False
