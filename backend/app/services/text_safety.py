# backend/app/services/text_safety.py
"""文本安全工具 — prompt 注入防御的统一实现。

从 app/api/ai_agent.py 下沉而来（原 FASTAPI-INJECT-001 修复），
供 ai_agent 与 data_search_service 等需要把"外部来源文本"拼进
system prompt 的调用方复用。
"""

from __future__ import annotations

import re

# 常见 prompt injection 模式（中英）
_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(?:previous|prior|above|all)\s+(?:instructions?|prompts?|rules?)"),
    re.compile(r"(?i)disregard\s+(?:previous|prior|above|all)\s+(?:instructions?|prompts?|rules?)"),
    re.compile(r"(?i)forget\s+(?:your|previous|prior)\s+(?:instructions?|rules?|prompts?)"),
    re.compile(r"(?i)you\s+are\s+(?:now|actually)\s+(?:a|an)\s+"),
    re.compile(r"(?i)^(?:system|assistant|developer)\s*:"),
    re.compile(r"(?:忽略|跳过|无视|忽略掉)(?:上述|之前|前面|以上|所有)(?:指令|提示|规则|约束)"),
    re.compile(r"(?:从现在起|从这一刻起)(?:你|请)(?:是|成为|扮演)"),
    re.compile(r"(?i)jailbreak"),
    re.compile(r"(?i)DAN\s+mode"),
]


def sanitize_prompt_input(text: str) -> str:
    """清洗外部来源文本，移除常见 prompt injection 模式。

    引用 FASTAPI-INJECT-001：外部输入必须与系统指令隔离，
    防止恶意内容劫持 system prompt 改变 LLM 行为。
    """
    if not text:
        return text
    cleaned = text
    for pattern in _PROMPT_INJECTION_PATTERNS:
        cleaned = pattern.sub("[FILTERED]", cleaned)
    return cleaned
