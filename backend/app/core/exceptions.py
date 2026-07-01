"""自定义异常类 — service 层使用，替代直接 raise HTTPException。"""


class BusinessError(Exception):
    """业务逻辑异常，默认 400。"""

    status_code: int = 400
    detail: str = "业务错误"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        # 允许实例级别覆盖默认 detail / status_code，同时保留类属性作为默认值
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(BusinessError):
    status_code = 404
    detail = "资源不存在"


class ForbiddenError(BusinessError):
    status_code = 403
    detail = "无权访问"
