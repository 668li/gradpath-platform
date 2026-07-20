"""集中式限流配置。

将所有 API 限流规则集中管理，便于调整和审计。
未来如需迁移到 throttled-py，只需替换本模块的实现。

使用方式：
    from app.core.rate_limit import rate_limits
    @limiter.limit(rate_limits.AUTH_LOGIN)
    def login(...): ...
"""
from __future__ import annotations


class RateLimitConfig:
    """限流规则集中配置。

    所有限流值以 "N/minute" 格式定义，便于阅读和调整。
    设计时遵循以下原则：
    - 认证类接口严格限流（防爆破）
    - AI 类接口中等限流（成本控制）
    - 读接口宽松限流（用户体验）
    """

    # ===== 认证类（防爆破） =====
    AUTH_REGISTER: str = "3/minute"  # 注册：3次/分钟
    AUTH_LOGIN: str = "5/minute"  # 登录：5次/分钟
    AUTH_REFRESH: str = "10/minute"  # 刷新令牌：10次/分钟

    # ===== AI 类（成本控制） =====
    AI_DECISION_ADVICE: str = "10/minute"  # AI 决策建议：10次/分钟
    AI_GROWTH_INSIGHT: str = "10/minute"  # AI 成长洞察：10次/分钟
    AI_CHAT: str = "20/minute"  # AI 对话：20次/分钟

    # ===== 写操作类（防滥用） =====
    RETROSPECTIVE_CREATE: str = "10/minute"  # 复盘创建：10次/分钟
    MENTOR_REVIEW_SUBMIT: str = "5/minute"  # 导师评价提交：5次/分钟
    EXPERIENCE_POST_CREATE: str = "5/minute"  # 经验贴创建：5次/分钟
    QA_QUESTION_CREATE: str = "5/minute"  # 问题创建：5次/分钟
    QA_ANSWER_CREATE: str = "5/minute"  # 回答创建：5次/分钟
    COMMUNITY_LIKE: str = "30/minute"  # 社区点赞：30次/分钟
    COMMENT_CREATE: str = "10/minute"  # 评论创建：10次/分钟

    # ===== 默认限流 =====
    DEFAULT: str = "60/minute"  # 默认：60次/分钟

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
