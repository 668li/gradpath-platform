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

    # 数据型 skill 声明自己负责注入的数据域（data_search_service 的 domain 名），
    # chat 通用数据搜索层据此去重，避免同一数据双注入。
    covered_data_domains: frozenset[str] = frozenset()

    @abstractmethod
    def should_activate(self, message: str, context: dict) -> bool:
        """判断是否应该激活此 Skill。"""

    @abstractmethod
    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        """构建 system prompt。"""

    @abstractmethod
    def build_user_prompt(self, message: str) -> str:
        """构建用户消息 prompt。"""

    def inject_data(self, db, user_id, content: str) -> str:
        """数据注入钩子（Phase C2，可选覆写）。

        数据型 skill 可覆写此方法，拉取专有数据（进面线/条件账本/测评/专业前景）
        拼成一段可被直接追加到 system prompt 的正文；通用 coach skill 保持默认空返回。

        Args:
            db: 数据库会话
            user_id: 当前用户 id（UUID/str）
            content: 用户本次消息原文（供按需筛选数据）

        Returns:
            注入的数据文本（可直接追加到 system prompt），无需数据时返回空字符串。
        """
        return ""

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出。默认返回原始文本。

        Returns:
            {"content": str, "career_plan": None}
        """
        return {"content": llm_output, "career_plan": None}
