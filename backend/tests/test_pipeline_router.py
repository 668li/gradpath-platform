# backend/tests/test_pipeline_router.py
"""智能路由测试。"""
from app.models.pipeline_enums import ContentType
from pipeline.router import (
    route_by_filename,
    route_by_mime,
    route_by_url,
    route_content,
)


class TestRouteByFilename:
    def test_pdf(self):
        assert route_by_filename("report.pdf") == ContentType.pdf

    def test_excel_xlsx(self):
        assert route_by_filename("data.xlsx") == ContentType.excel

    def test_excel_xls(self):
        assert route_by_filename("data.xls") == ContentType.excel

    def test_csv(self):
        assert route_by_filename("data.csv") == ContentType.csv

    def test_html(self):
        assert route_by_filename("page.html") == ContentType.html

    def test_unknown_extension(self):
        assert route_by_filename("file.xyz") is None

    def test_no_extension(self):
        assert route_by_filename("noextension") is None

    def test_case_insensitive(self):
        assert route_by_filename("REPORT.PDF") == ContentType.pdf


class TestRouteByMime:
    def test_pdf_mime(self):
        assert route_by_mime("application/pdf") == ContentType.pdf

    def test_csv_mime(self):
        assert route_by_mime("text/csv") == ContentType.csv

    def test_unknown_mime(self):
        assert route_by_mime("application/unknown") is None


class TestRouteByUrl:
    def test_url_with_pdf(self):
        assert route_by_url("https://example.com/report.pdf") == ContentType.pdf

    def test_url_with_excel(self):
        assert route_by_url("https://example.com/data.xlsx") == ContentType.excel

    def test_url_no_extension(self):
        assert route_by_url("https://example.com/page") == ContentType.html

    def test_url_with_path_and_query(self):
        assert route_by_url("https://example.com/report.pdf?download=1") == ContentType.pdf


class TestRouteContent:
    def test_filename_priority(self):
        result = route_content(filename="report.pdf", mime_type="text/html")
        assert result == ContentType.pdf

    def test_mime_when_no_filename(self):
        result = route_content(mime_type="application/pdf")
        assert result == ContentType.pdf

    def test_url_when_no_filename_mime(self):
        result = route_content(url="https://example.com/data.csv")
        assert result == ContentType.csv

    def test_default_html(self):
        result = route_content()
        assert result == ContentType.html

    def test_llm_fallback_not_called_without_key(self, monkeypatch):
        # 没有配置 LLM_API_KEY 时不调用 LLM
        from app.config import settings
        monkeypatch.setattr(settings, "LLM_API_KEY", "")
        result = route_content(content_preview="some content")
        assert result == ContentType.html
