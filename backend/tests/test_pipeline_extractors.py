# backend/tests/test_pipeline_extractors.py
"""文本提取器测试。"""
from pathlib import Path

from app.models.pipeline_enums import ContentType
from pipeline.extractors.csv_extractor import extract_csv
from pipeline.extractors.html_extractor import extract_html

FIXTURES = Path(__file__).parent / "fixtures"


class TestHtmlExtractor:
    def test_basic_extraction(self):
        html = "<html><body><h1>标题</h1><p>内容</p></body></html>"
        result = extract_html(html)
        assert result.content_type == ContentType.html
        assert "标题" in result.text
        assert "内容" in result.text

    def test_removes_script_style(self):
        html = "<html><body><script>alert(1)</script><style>.x{}</style><p>text</p></body></html>"
        result = extract_html(html)
        assert "alert" not in result.text
        assert ".x{}" not in result.text
        assert "text" in result.text

    def test_removes_nav_footer(self):
        html = "<html><body><nav>菜单</nav><main>正文</main><footer>页脚</footer></body></html>"
        result = extract_html(html)
        assert "菜单" not in result.text
        assert "页脚" not in result.text
        assert "正文" in result.text

    def test_fixture_file(self):
        html_file = FIXTURES / "sample_report.html"
        result = extract_html(html_file.read_text(encoding="utf-8"))
        assert "清华大学" in result.text
        assert "计算机科学与技术" in result.text


class TestCsvExtractor:
    def test_basic_csv(self):
        csv_content = "专业,就业率,升学率\n计算机,0.45,0.35\n电子,0.50,0.30\n"
        result = extract_csv(csv_content)
        assert result.content_type == ContentType.csv
        assert "专业" in result.text
        assert "计算机" in result.text
        assert result.metadata["row_count"] == 3

    def test_tab_delimited(self):
        csv_content = "a\tb\n1\t2\n"
        result = extract_csv(csv_content)
        assert result.metadata["col_count"] == 2

    def test_semicolon_delimited(self):
        csv_content = "a;b\n1;2\n"
        result = extract_csv(csv_content)
        assert result.metadata["col_count"] == 2

    def test_empty_csv(self):
        result = extract_csv("")
        assert result.text == ""
        assert result.metadata["row_count"] == 0

    def test_fixture_file(self):
        csv_file = FIXTURES / "sample_report.csv"
        result = extract_csv(csv_file.read_text(encoding="utf-8"))
        assert "计算机科学与技术" in result.text
        assert result.metadata["row_count"] == 3
