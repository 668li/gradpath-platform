"""自定义业务异常 — service 层使用，替代直接 raise HTTPException。

统一异常体系（C2 改造）：
- BusinessError: 业务逻辑异常基类，默认 400
- NotFoundError: 资源不存在，404
- ForbiddenError: 无权访问，403
- ValidationFailedError: 参数校验失败，422
- RateLimitExceededError: 请求过于频繁，429

每个异常都携带：
- code: 业务错误码（大写蛇形），便于前端按 code 分支处理
- message: 用户可读的错误消息
- status_code: HTTP 状态码
- details: 可选的额外详情（如字段级校验错误）
"""


class BusinessError(Exception):
    """业务逻辑异常基类，默认 400。

    用法：
        raise BusinessError("USER_EXISTS", "该邮箱已注册", 409)
        raise BusinessError("QUOTA_EXCEEDED", "今日 AI 调用次数已用尽", 429,
                            details={"quota": 100, "used": 100})
    """

    def __init__(
        self,
        code: str = "BUSINESS_ERROR",
        message: str = "业务错误",
        status_code: int = 400,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        # 兼容旧代码读取 .detail 属性
        self.detail = message
        super().__init__(message)


class NotFoundError(BusinessError):
    """资源不存在（404）。"""

    def __init__(self, message: str = "资源不存在", details: dict | None = None):
        super().__init__("NOT_FOUND", message, 404, details)


class ForbiddenError(BusinessError):
    """无权访问（403）。"""

    def __init__(self, message: str = "无权访问", details: dict | None = None):
        super().__init__("FORBIDDEN", message, 403, details)


class ValidationFailedError(BusinessError):
    """参数校验失败（422）。"""

    def __init__(
        self,
        message: str = "参数校验失败",
        details: dict | None = None,
    ):
        super().__init__("VALIDATION_FAILED", message, 422, details)


class RateLimitExceededError(BusinessError):
    """请求过于频繁（429）。"""

    def __init__(self, message: str = "请求过于频繁", details: dict | None = None):
        super().__init__("RATE_LIMIT_EXCEEDED", message, 429, details)


class AuthenticationError(BusinessError):
    """未认证或认证失败（401）。"""

    def __init__(self, message: str = "未登录或登录已过期", details: dict | None = None):
        super().__init__("AUTHENTICATION_FAILED", message, 401, details)


class ConflictError(BusinessError):
    """资源冲突（409），如邮箱已注册。"""

    def __init__(self, message: str = "资源已存在", details: dict | None = None):
        super().__init__("CONFLICT", message, 409, details)
