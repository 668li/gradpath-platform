"""考研资讯 LLM 结构化增强（Phase C2）。

对审核确认入库的 kaoyan_news 异步生成 ai_summary（信息差摘要）+ 精确化
key_dates + category 修正。失败/超时降级保留规则版结果（Phase C1 在
promote 落库时已计算 quality_score/key_dates/is_expired），不阻塞主流程。

降级模式与 ai_butler_service 一致：LLM 是可选增强，规则版结果永远可用；
LLM 不可用时 ai_summary 保持 NULL（诚实，不伪造 AI 内容），前端回退展示
summary 字段。
"""
import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.kaoyan_news import KaoyanNews

logger = logging.getLogger(__name__)

# 单条 LLM 调用超时（秒）— 批量任务串行处理，超时即降级该条
LLM_TIMEOUT = 25
# LLM 输出摘要长度约束
SUMMARY_MAX_LEN = 160
# 有效分类维度（与 transformer.KAOYAN_CATEGORY_RULES 键集一致）
VALID_CATEGORIES = {
    "政策", "招生简章", "复试", "调剂", "复试线", "推免", "报录比", "择校", "备考", "general",
}

_SYSTEM_PROMPT = (
    "你是考研信息差分析师。基于给定的考研资讯标题与正文，输出严格 JSON（不要任何其他文字）："
    "{\"summary\": \"≤120字中文摘要，只写对考生有行动价值的信息差（截止时间、报名要求、政策变化点），不编造原文没有的事实\", "
    "\"category\": \"资讯分类，从以下取值：政策/招生简章/复试/调剂/复试线/推免/报录比/择校/备考/general\", "
    "\"key_dates\": [{\"label\": \"报名|网上确认|截止|初试|复试|调剂\", \"date\": \"YYYY-MM-DD\", \"end_date\": \"YYYY-MM-DD(可选，窗口结束日)\"}]}。"
    "关键时间点只从原文抽取，原文没有的日期一律不写。"
)


def _build_user_prompt(title: str, category: str, content: str) -> str:
    return (
        f"标题：{title}\n"
        f"现有分类：{category}\n"
        f"正文：{(content or '')[:2000]}"
    )


def _parse_llm_json(text: str) -> dict | None:
    """解析 LLM 返回的 JSON（容忍 markdown 代码块与前后缀噪音）。"""
    if not text:
        return None
    cleaned = text.strip()
    # 去掉 ```json ... ``` 围栏
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.S)
    if fence:
        cleaned = fence.group(1)
    # 取第一个 { 到最后一个 }（容忍前后缀文字）
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None


def _valid_date_token(value: object) -> str | None:
    """校验并归一化日期字符串 'YYYY-MM-DD'。"""
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        year, month, day = (int(p) for p in value.strip().split("-"))
        if 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
            return value.strip()
    return None


def _sanitize_llm_dates(raw_dates: object) -> list[dict]:
    """把 LLM 输出的 key_dates 清洗为 [{label, date, end_date?}]；非法条目丢弃。"""
    if not isinstance(raw_dates, list):
        return []
    cleaned: list[dict] = []
    for item in raw_dates:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or label not in {
            "报名", "网上确认", "截止", "初试", "复试", "调剂",
        }:
            continue
        date = _valid_date_token(item.get("date"))
        if not date:
            continue
        entry = {"label": label, "date": date}
        end_date = _valid_date_token(item.get("end_date"))
        if end_date and end_date >= date:
            entry["end_date"] = end_date
        cleaned.append(entry)
    return cleaned


def _rule_based_summary(news: KaoyanNews) -> str | None:
    """LLM 不可用时的规则兜底摘要：由已存 key_dates 生成确定性时间提示。"""
    parts = []
    for kd in (news.key_dates or [])[:3]:
        label, date = kd.get("label", ""), kd.get("date", "")
        if kd.get("end_date"):
            parts.append(f"{label} {date}~{kd['end_date']}")
        elif date:
            parts.append(f"{label} {date}")
    if parts:
        return "关键时间：" + "；".join(parts)
    return None


async def enhance_news_item(db: Session, news: KaoyanNews) -> dict:
    """单条资讯 LLM 增强（ai_summary + 精确 key_dates + category）。

    成功：回填 ai_summary/key_dates/category，并基于新日期重算 is_expired。
    失败/超时/未配置：保留规则版结果，ai_summary 不动（诚实降级），返回 degraded。
    不 commit —— 由调用方（Celery 任务）统一提交。
    """
    try:
        from app.services.ai_orchestrator import AIOrchestrator

        ai = AIOrchestrator()
        raw = await ai.chat(
            _SYSTEM_PROMPT,
            _build_user_prompt(news.title, news.category, news.content or ""),
            timeout=LLM_TIMEOUT,
        )
        parsed = _parse_llm_json(raw)
        if not parsed:
            logger.info("[news_enhance] LLM 输出非 JSON，降级 %s", news.id)
            return {"status": "degraded", "reason": "invalid_llm_json"}

        summary = parsed.get("summary")
        if isinstance(summary, str) and summary.strip():
            news.ai_summary = summary.strip()[:SUMMARY_MAX_LEN]

        category = parsed.get("category")
        if isinstance(category, str) and category in VALID_CATEGORIES:
            news.category = category

        llm_dates = _sanitize_llm_dates(parsed.get("key_dates"))
        if llm_dates:
            news.key_dates = llm_dates
            # 关键日期可能变化 → 基于新日期重算时效标记
            from app.services.research_promote import _compute_is_expired

            news.is_expired = _compute_is_expired(
                news.published_at, news.crawled_at, llm_dates
            )

        logger.info(
            "[news_enhance] 增强成功 %s (summary=%s, key_dates=%d)",
            news.id, bool(news.ai_summary), len(news.key_dates or []),
        )
        return {"status": "enhanced", "key_dates": len(llm_dates)}
    except Exception as e:  # noqa: BLE001 — 降级模式：任何失败保留规则版结果
        logger.warning("[news_enhance] LLM 增强失败降级 %s: %s", news.id, e)
        return {"status": "degraded", "reason": str(e)}


def schedule_news_enhancement(limit: int = 5) -> bool:
    """投递批量增强任务到 Celery ai 队列（fire-and-forget）。

    broker 不可用（开发环境 memory://）时跳过，不阻塞审核主流程。
    返回是否成功投递。
    """
    try:
        from app.celery_app import celery_app
        from app.config import settings

        if not settings.REDIS_URL or str(celery_app.conf.broker_url).startswith("memory://"):
            return False
        from app.tasks.ai_tasks import enhance_kaoyan_news_batch

        enhance_kaoyan_news_batch.delay(limit=limit)
        logger.info("[news_enhance] 已投递批量增强任务 limit=%d", limit)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[news_enhance] 投递增强任务失败（跳过）: %s", e)
        return False
