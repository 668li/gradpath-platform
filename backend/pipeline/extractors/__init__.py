# backend/pipeline/extractors/__init__.py
from dataclasses import dataclass, field

from app.models.pipeline_enums import ContentType


@dataclass
class ExtractResult:
    """文本提取器统一输出。"""
    text: str
    content_type: ContentType
    metadata: dict = field(default_factory=dict)
