# backend/app/skills/user_referral.py
"""用户推荐助手 Skill — 帮助用户生成推荐链接，追踪推荐效果，提供推荐奖励。"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "推荐朋友", "邀请好友", "推荐链接", "user referral", "邀请注册",
]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含推荐链接生成与奖励说明",
  "referral_info": {
    "referral_code": "推荐码",
    "referral_link": "推荐链接",
    "reward_tiers": [{"tier": "等级", "referrals_needed": 0, "reward": "奖励内容", "description": "说明"}],
    "share_templates": {"wechat": "微信分享文案", "weibo": "微博分享文案", "general": "通用分享文案"},
    "tracking": {"total_referrals": 0, "successful_referrals": 0, "pending_referrals": 0, "rewards_earned": 0},
    "faq": [{"question": "常见问题", "answer": "解答"}]
  }
}"""


class UserReferralSkill(BaseSkill):
    """用户推荐助手 Skill。"""

    code = "user_referral"
    name = "user_referral"
    display_name = "用户推荐助手"
    description = "帮助用户生成推荐链接，追踪推荐效果，提供推荐奖励"
    icon = "users"

    def should_activate(self, message: str, context: dict) -> bool:
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in ACTIVATE_KEYWORDS)

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        knowledge_block = ""
        if knowledge:
            lines = ["【相关知识库参考】"]
            for k in knowledge:
                lines.append(f"- 《{k.get('title', '')}》[{k.get('category', '')}]")
                content = (k.get("content") or "")[:200]
                if content:
                    lines.append(f"  摘要：{content}")
            knowledge_block = "\n".join(lines) + "\n\n"

        return (
            "你是 GradPath 用户推荐助手，擅长帮助用户通过社交分享获取推荐奖励。\n\n"
            "你的任务：为用户生成个性化的推荐链接，介绍推荐奖励机制，提供分享文案模板。\n"
            "功能包括：\n"
            "1. 生成唯一推荐码和推荐链接\n"
            "2. 介绍分层推荐奖励机制\n"
            "3. 提供多平台分享文案模板\n"
            "4. 展示推荐效果追踪数据\n"
            "5. 解答推荐相关常见问题\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- reward_tiers 至少给 3 个等级\n"
            "- share_templates 至少提供 2 种平台文案\n"
            "- faq 至少 2 个常见问题\n"
            "- 所有内容使用中文，语气友好热情\n"
            "- 结合用户画像给出个性化建议\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户推荐咨询】\n{message}\n\n请基于以上信息生成推荐方案（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 referral_info 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        ref_raw = data.get("referral_info")

        referral_info = None
        if isinstance(ref_raw, dict):
            referral_info = _coerce_referral_info(ref_raw)

        return {"content": content, "referral_info": referral_info}


def _safe_parse_json(content: str) -> dict:
    """容错解析 LLM 返回的 JSON。"""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    return {"content": content, "referral_info": None}


def _coerce_referral_info(raw: dict) -> dict:
    """将解析后的 referral_info dict 强制转换为标准结构。"""
    def _as_dict(v) -> dict:
        return v if isinstance(v, dict) else {}

    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    return {
        "referral_code": str(raw.get("referral_code", "")),
        "referral_link": str(raw.get("referral_link", "")),
        "reward_tiers": _as_list(raw.get("reward_tiers")),
        "share_templates": _as_dict(raw.get("share_templates")),
        "tracking": _as_dict(raw.get("tracking")),
        "faq": _as_list(raw.get("faq")),
    }
