"""外部验证（D9 Phase 2.2）——claim-driven verification。

流程（拍板 §六）：证据需要外部核查 → 提供来源 URL → SSRF 安全闸
（crawlers.url_safety.validate_outbound_url，重定向逐跳校验）→ 拉取正文
（timeline_service.html_to_text）→ AI 比对立场 → 推进验证状态。

不覆盖旧数据（拍板禁令 §十三.14）：contradict 时原证据改 contradicted 留痕，
并新建一条外部证据行（stance=contradicting、externally_verified、来源=该 URL）；
agree/stale 推进原证据；unrelated 不动任何状态。
AI 不可用=503 诚实失败——绝不静默放行把无来源证据标成 VERIFIED。
"""

import json
import logging
import re
from datetime import date
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, ValidationFailedError
from app.crawlers.url_safety import validate_outbound_url
from app.models.decision_os import (
    DecisionEvidence,
    EvidenceReliability,
    EvidenceSourceType,
    EvidenceStance,
    EvidenceVerificationStatus,
)
from app.services.ai_orchestrator import AIOrchestrator
from app.services.decision_os_service import get_evidence
from app.services.timeline_service import html_to_text

logger = logging.getLogger(__name__)

_MAX_HOPS = 3
_MAX_BYTES = 100_000
_TIMEOUT = 15.0

_SYSTEM_PROMPT = """你是证据核查员。给定【原证据】与【外部网页正文】，判断该外部来源对原证据的立场。

严格输出 JSON（不要输出任何其他内容）：
{"verdict": "agree|contradict|unrelated|stale", "summary": "一句话：外部来源说了什么、与原证据的关系"}
- agree：外部来源支持原证据的关键内容
- contradict：外部来源与原证据关键内容矛盾
- stale：外部信息明显更旧，原证据已是更新状态
- unrelated：网页与该证据无关（或正文无实质内容）
summary 不得编造网页中没有的内容。"""


def _fetch_text(url: str) -> str:
    """拉取外部页面正文。每跳都过 SSRF 闸；带字节上限。测试可打桩。"""
    current = url
    for _ in range(_MAX_HOPS):
        ok, reason = validate_outbound_url(current)
        if not ok:
            raise ValidationFailedError(f"外部来源被安全闸拒绝：{reason}")
        try:
            resp = httpx.get(
                current,
                timeout=_TIMEOUT,
                follow_redirects=False,
                headers={"User-Agent": "GradPath-EvidenceVerify/1.0"},
            )
        except httpx.HTTPError as exc:
            raise BusinessError("FETCH_FAILED", f"外部来源拉取失败：{exc}", 400)
        if resp.is_redirect:
            location = resp.headers.get("location", "")
            if not location:
                break
            current = str(httpx.URL(resp.url).join(location))
            continue
        resp.raise_for_status()
        return html_to_text(resp.content[:_MAX_BYTES])
    raise ValidationFailedError("重定向次数过多")


async def _ai_compare(claim: str, page_text: str) -> dict:
    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=f"【原证据】{claim}\n\n【外部网页正文】{page_text[:4000]}",
        timeout=30,
    )
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{.*\}", raw or "", re.DOTALL)
        if not match:
            raise BusinessError("AI_OUTPUT_INVALID", "核查 AI 返回不可解析", 503)
        try:
            data = json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            raise BusinessError("AI_OUTPUT_INVALID", "核查 AI 返回不可解析", 503)
    if not isinstance(data, dict) or data.get("verdict") not in (
        "agree",
        "contradict",
        "unrelated",
        "stale",
    ):
        raise BusinessError("AI_OUTPUT_INVALID", "核查 AI 返回立场非法", 503)
    return data


async def verify_with_external_source(db: Session, user_id, evidence_id, source_url: str) -> dict:
    """用外部来源核查一条证据，按立场推进验证状态（证据闸唯一推进入口之一）。"""
    evidence = get_evidence(db, user_id, evidence_id)

    page_text = _fetch_text(source_url)
    if not page_text or len(page_text) < 20:
        raise BusinessError("EMPTY_PAGE", "外部页面无实质正文，无法核查", 400)

    try:
        data = await _ai_compare(evidence.claim, page_text[:4000])
    except BusinessError:
        raise
    except Exception as exc:  # LLM 不可用/网络失败：诚实 503，证据状态未改动
        raise BusinessError("AI_UNAVAILABLE", f"核查 AI 暂不可用，证据状态未改动：{exc}", 503)
    verdict = data["verdict"]
    summary = str(data.get("summary") or "").strip()[:500]

    today = date.today()
    changed = True
    new_evidence: DecisionEvidence | None = None

    if verdict == "agree":
        evidence.verification_status = EvidenceVerificationStatus.externally_verified
        evidence.verification_source = source_url
        evidence.verified_on = today
    elif verdict == "stale":
        evidence.verification_status = EvidenceVerificationStatus.stale
        evidence.verification_source = source_url
        evidence.verified_on = None
    elif verdict == "contradict":
        # 冲突不覆盖：原证据留痕为 contradicted，外部说法另立一行
        evidence.verification_status = EvidenceVerificationStatus.contradicted
        evidence.verification_source = source_url
        evidence.verified_on = today
        domain = urlparse(source_url).hostname or source_url
        new_evidence = DecisionEvidence(
            user_id=evidence.user_id,
            decision_id=evidence.decision_id,
            hypothesis_id=evidence.hypothesis_id,
            claim=f"外部来源（{domain}）：{summary}",
            source=domain,
            source_url=source_url,
            source_type=EvidenceSourceType.media,
            reliability=EvidenceReliability.medium,
            stance=EvidenceStance.contradicting,
            provider=f"external:{domain}",
            verification_status=EvidenceVerificationStatus.externally_verified,
            verification_source=source_url,
            verified_on=today,
        )
        db.add(new_evidence)
    else:  # unrelated
        changed = False

    db.commit()
    db.refresh(evidence)
    if new_evidence is not None:
        db.refresh(new_evidence)
    return {
        "verdict": verdict,
        "summary": summary,
        "changed": changed,
        "evidence": evidence,
        "new_evidence": new_evidence,
    }
