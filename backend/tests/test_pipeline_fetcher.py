# backend/tests/test_pipeline_fetcher.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from pipeline.fetcher import fetch_report, check_robots_allowed


SAMPLE_HTML = """
<html><body>
<h1>清华大学2024届毕业生就业质量年度报告</h1>
<table>
<tr><th>专业</th><th>毕业人数</th><th>就业率</th></tr>
<tr><td>机械工程</td><td>120</td><td>45%</td></tr>
</table>
</body></html>
"""


class TestFetcher:
    def test_fetch_html_report(self, db_session):
        """测试成功抓取 HTML 报告"""
        school = School(name="清华大学", slug="tsinghua", report_index_url="https://career.tsinghua.edu.cn/")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.check_robots_allowed", return_value=True), \
             patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(db_session, school_slug="tsinghua", year=2024)

        assert report is not None
        assert report.school_id == school.id
        assert report.year == 2024
        assert report.parse_status == ParseStatus.pending
        assert "清华大学2024届" in report.raw_html

    def test_fetch_report_not_found(self, db_session):
        """测试报告链接未找到"""
        school = School(name="清华大学", slug="tsinghua", report_index_url="https://career.tsinghua.edu.cn/")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.check_robots_allowed", return_value=True), \
             patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            report = fetch_report(db_session, school_slug="tsinghua", year=2024)

        assert report is not None
        assert report.parse_status == ParseStatus.failed
        assert "404" in (report.parse_error or "")

    def test_fetch_school_not_found(self, db_session):
        """测试学校不存在"""
        report = fetch_report(db_session, school_slug="nonexistent", year=2024)
        assert report is None

    def test_fetch_direct_url(self, db_session):
        """测试直接提供报告 URL"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()

        direct_url = "https://example.com/report.htm"
        with patch("pipeline.fetcher.check_robots_allowed", return_value=True) as mock_robots, \
             patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(
                db_session,
                school_slug="tsinghua",
                year=2024,
                direct_url=direct_url,
            )

        assert report is not None
        assert report.source_url == "https://example.com/report.htm"
        # B2: 主流程应调用 robots 校验
        mock_robots.assert_called_once_with(direct_url)

    def test_fetch_robots_disallowed(self, db_session):
        """B2: robots.txt 禁止抓取时应返回 failed 状态且不发起 HTTP 请求"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()

        direct_url = "https://example.com/report.htm"
        with patch("pipeline.fetcher.check_robots_allowed", return_value=False) as mock_robots, \
             patch("pipeline.fetcher.httpx.get") as mock_get:
            # 即便 httpx.get 返回 200，robots 禁止时也不应走到抓取逻辑
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(
                db_session,
                school_slug="tsinghua",
                year=2024,
                direct_url=direct_url,
            )

        assert report is not None
        assert report.parse_status == ParseStatus.failed
        assert report.parse_error is not None
        assert "robots" in report.parse_error.lower()
        # robots 校验被调用
        mock_robots.assert_called_once_with(direct_url)
        # 禁止抓取时不应发起 HTTP 请求
        mock_get.assert_not_called()

    def test_check_robots_fail_closed(self):
        """W5: robots.txt 读取异常时应 fail-closed 返回 False（而非默认放行）"""
        with patch("pipeline.fetcher.RobotFileParser") as MockParser:
            instance = MockParser.return_value
            instance.read.side_effect = Exception("network error")
            result = check_robots_allowed("https://example.com")

        assert result is False
