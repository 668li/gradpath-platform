"""集中式限流配置。

将所有 API 限流规则集中管理，便于调整和审计。
未来如需迁移到 throttled-py，只需替换本模块的实现。

使用方式：
    from app.core.rate_limit import rate_limits
    @limiter.limit(rate_limits.AUTH_LOGIN)
    def login(...): ...

每个规则支持通过环境变量 RATE_LIMIT_<KEY> 覆盖（如 E2E 测试环境放宽注册限流），
未设置时使用内置默认值，生产行为不受影响。
"""

from __future__ import annotations

import os


def _rule(env_key: str, default: str) -> str:
    """读取单个限流规则的配置值；环境变量未设置时回退到默认值。"""
    return os.getenv(f"RATE_LIMIT_{env_key}", default)


class RateLimitConfig:
    """限流规则集中配置。

    所有限流值以 "N/minute" 格式定义，便于阅读和调整。
    设计时遵循以下原则：
    - 认证类接口严格限流（防爆破）
    - AI 类接口中等限流（成本控制）
    - 读接口宽松限流（用户体验）
    """

    # ===== 认证类（防爆破） =====
    AUTH_REGISTER: str = _rule("AUTH_REGISTER", "3/minute")  # 注册：3次/分钟
    AUTH_LOGIN: str = _rule("AUTH_LOGIN", "5/minute")  # 登录：5次/分钟
    AUTH_REFRESH: str = _rule("AUTH_REFRESH", "10/minute")  # 刷新令牌：10次/分钟
    AUTH_FORGOT_PASSWORD: str = _rule("AUTH_FORGOT_PASSWORD", "3/minute")
    AUTH_RESET_PASSWORD: str = _rule("AUTH_RESET_PASSWORD", "5/minute")
    AUTH_CHANGE_PASSWORD: str = _rule("AUTH_CHANGE_PASSWORD", "5/minute")

    # ===== AI 类（成本控制） =====
    AI_DECISION_ADVICE: str = _rule("AI_DECISION_ADVICE", "10/minute")  # AI 决策建议：10次/分钟
    AI_GROWTH_INSIGHT: str = _rule("AI_GROWTH_INSIGHT", "10/minute")  # AI 成长洞察：10次/分钟
    AI_CHAT: str = _rule("AI_CHAT", "20/minute")  # AI 对话：20次/分钟
    RETROSPECTIVE_AI_DRAFT: str = _rule("RETROSPECTIVE_AI_DRAFT", "10/minute")

    # ===== 写操作类（防滥用） =====
    RETROSPECTIVE_CREATE: str = _rule("RETROSPECTIVE_CREATE", "10/minute")  # 复盘创建：10次/分钟
    MENTOR_REVIEW_SUBMIT: str = _rule("MENTOR_REVIEW_SUBMIT", "5/minute")  # 导师评价提交：5次/分钟
    EXPERIENCE_POST_CREATE: str = _rule(
        "EXPERIENCE_POST_CREATE", "5/minute"
    )  # 经验贴创建：5次/分钟
    QA_QUESTION_CREATE: str = _rule("QA_QUESTION_CREATE", "5/minute")  # 问题创建：5次/分钟
    QA_ANSWER_CREATE: str = _rule("QA_ANSWER_CREATE", "5/minute")  # 回答创建：5次/分钟
    COMMUNITY_LIKE: str = _rule("COMMUNITY_LIKE", "30/minute")  # 社区点赞：30次/分钟
    COMMENT_CREATE: str = _rule("COMMENT_CREATE", "10/minute")  # 评论创建：10次/分钟
    QUALITY_FEEDBACK_CREATE: str = _rule(
        "QUALITY_FEEDBACK_CREATE", "5/minute"
    )  # 质量分反馈：5次/分钟（Phase I）
    REPORT_CREATE: str = _rule("REPORT_CREATE", "5/minute")

    # ===== 默认限流 =====
    DEFAULT: str = _rule("DEFAULT", "60/minute")  # 默认：60次/分钟

    @classmethod
    def get_all_rules(cls) -> dict[str, str]:
        """返回所有限流规则的字典表示，用于审计和文档。"""
        return {
            key: value
            for key, value in vars(cls).items()
            if not key.startswith("_") and isinstance(value, str) and "/" in value
        }


# 全局实例
rate_limits = RateLimitConfig()
