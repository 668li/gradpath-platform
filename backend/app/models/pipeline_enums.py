# backend/app/models/pipeline_enums.py
import enum


class SourceType(str, enum.Enum):
    crawl = "crawl"
    upload = "upload"
    api = "api"


class ContentType(str, enum.Enum):
    html = "html"
    pdf = "pdf"
    excel = "excel"
    csv = "csv"
    json = "json"
