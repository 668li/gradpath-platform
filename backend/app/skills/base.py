# backend/app/skills/base.py
"""Skill 抽象基类 — 定义所有 Skill 插件的统一接口。

每个 Skill 负责：
1. 判断是否应该激活（should_activate）
2. 构建 system prompt（build_system_prompt）
3. 构建用户消息 prompt（build_user_prompt）
4. 解析 LLM 输出（parse_response，默认返回原始文本）
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """Skill 抽象基类。"""

    code: str = ""
    name: str = ""
    description: str = ""
    icon: str = ""

    @abstractmethod
    def should_activate(self, message: str, context: dict) -> bool:
        """判断是否应该激活此 Skill。"""

    @abstractmethod
    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        """构建 system prompt。"""

    @abstractmethod
    def build_user_prompt(self, message: str) -> str:
        """构建用户消息 prompt。"""

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出。默认返回原始文本。

        Returns:
            {"content": str, "career_plan": None}
        """
        return {"content": llm_output, "career_plan": None}
