# backend/tests/test_pipeline_extractor.py
import asyncio
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from pipeline.extractor import extract_report, call_llm


SAMPLE_REPORT_HTML = """
<html><body>
<h1>清华大学2024届毕业生就业质量年度报告</h1>
<h2>机械工程</h2>
<p>毕业人数：120人，就业率45%，升学率35%</p>
<table><tr><td>三一重工</td><td>15</td></tr></table>
</body></html>
"""

MOCK_LLM_RESPONSE = json.dumps({
    "majors": [
        {
            "major": "机械工程",
            "degree": "bachelor",
            "total_graduates": 120,
            "employment_rate": 0.45,
            "further_study_rate": 0.35,
            "civil_service_rate": 0.10,
            "abroad_rate": 0.10,
            "startup_rate": 0.0,
            "gap_year_rate": 0.0,
            "employer_ranking": [{"name": "三一重工", "count": 15}],
            "industry_distribution": {"制造业": 0.4, "互联网": 0.2},
            "destination_region": {"北京": 0.3, "上海": 0.15},
            "school_for_further_study": [{"name": "清华大学", "count": 20}]
        }
    ]
})

# 含单个非法 degree 值的 LLM 响应（用于 B3 容错测试）
MOCK_LLM_RESPONSE_BAD_DEGREE = json.dumps({
    "majors": [
        {
            "major": "坏专业",
            "degree": "diploma",  # 非法 degree 值，不在 Degree 枚举内
            "total_graduates": 50,
            "employment_rate": 0.5,
        },
        {
            "major": "好专业",
            "degree": "bachelor",
            "total_graduates": 100,
            "employment_rate": 0.6,
        }
    ]
})

# 只含单个专业的 LLM 响应（用于 W4 幂等性测试，与默认响应不同）
MOCK_LLM_RESPONSE_SINGLE = json.dumps({
    "majors": [
        {
            "major": "计算机科学",
            "degree": "master",
            "total_graduates": 80,
            "employment_rate": 0.7,
        }
    ]
})


class TestExtractor:
    def test_extract_success(self, db_session):
        """测试 LLM 解析成功"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", new=AsyncMock(return_value=MOCK_LLM_RESPONSE)):
            asyncio.run(extract_report(db_session, report_id=report.id))

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.parsed
        assert report.parsed_at is not None

        data = db_session.query(EmploymentData).filter(EmploymentData.report_id == report.id).all()
        assert len(data) == 1
        assert data[0].major == "机械工程"
        assert data[0].employment_rate == 0.45
        assert data[0].employer_ranking == [{"name": "三一重工", "count": 15}]

    def test_extract_llm_failure(self, db_session):
        """测试 LLM 返回无效 JSON"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", new=AsyncMock(return_value="not valid json")):
            asyncio.run(extract_report(db_session, report_id=report.id))

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.failed
        assert report.parse_error is not None

    def test_extract_no_html(self, db_session):
        """测试无 raw_html"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=None,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        result = asyncio.run(extract_report(db_session, report_id=report.id))
        assert result is None

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.failed

    def test_call_llm_payload_has_no_timeout_field(self):
        """B1: call_llm 通过 AIOrchestrator 调用，timeout 是传输层参数不应进入 LLM payload。

        修复: call_llm 已重构为使用 AIOrchestrator（统一 LLM 入口），
        不再直接调用 httpx.post。本测试验证 AIOrchestrator.chat 被正确调用，
        且 timeout 作为调用参数（而非 payload 字段）传递。
        """
        with patch("pipeline.extractor.AIOrchestrator") as MockOrch:
            mock_orch = MagicMock()
            mock_orch.chat = AsyncMock(return_value='{"majors": []}')
            MockOrch.return_value = mock_orch

            asyncio.run(call_llm("测试文本"))

            # AIOrchestrator.chat 应被调用，timeout 作为关键字参数传递
            assert mock_orch.chat.called
            call_kwargs = mock_orch.chat.call_args.kwargs
            # timeout 应作为调用参数（传输层），而非进入 prompt/payload
            assert call_kwargs.get("timeout") == 60, "timeout 应作为调用参数传递"
            # system_prompt 和 user_prompt 是字符串，不应包含 timeout 字段
            assert "timeout" not in call_kwargs.get("system_prompt", "")
            assert "timeout" not in call_kwargs.get("user_prompt", "")

    def test_extract_bad_degree_skipped(self, db_session):
        """B3: 单个坏 degree 值应跳过该专业，不影响其他专业与整份报告解析。"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", new=AsyncMock(return_value=MOCK_LLM_RESPONSE_BAD_DEGREE)):
            result = asyncio.run(extract_report(db_session, report_id=report.id))

        db_session.refresh(report)
        # 整份报告应解析成功，而非 failed
        assert report.parse_status == ParseStatus.parsed
        assert result is not None

        data = db_session.query(EmploymentData).filter(
            EmploymentData.report_id == report.id
        ).all()
        # 仅保留合法专业，坏专业被跳过
        majors = {d.major for d in data}
        assert "好专业" in majors
        assert "坏专业" not in majors
        assert len(data) == 1

    def test_extract_idempotent_clears_old_data(self, db_session):
        """W4: 重新解析应先清除该 report 已有的 EmploymentData，避免残留。"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        # 预置一条旧数据（不应出现在重新解析结果中）
        old_emp = EmploymentData(
            report_id=report.id,
            major="旧残留专业",
            degree=Degree.bachelor,
            total_graduates=999,
        )
        db_session.add(old_emp)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", new=AsyncMock(return_value=MOCK_LLM_RESPONSE_SINGLE)):
            asyncio.run(extract_report(db_session, report_id=report.id))

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.parsed

        data = db_session.query(EmploymentData).filter(
            EmploymentData.report_id == report.id
        ).all()
        majors = {d.major for d in data}
        # 旧残留数据应被清除
        assert "旧残留专业" not in majors
        # 新数据存在
        assert "计算机科学" in majors
        assert len(data) == 1
