"""溯源过滤闸门测试 — grad_scoreline_records 的 data_sources 可信判定。

背景：生产表混有程序合成假数据（伪造 data_sources=["院校研究生院官网", "研招网"]，
无具体溯源）。闸门规则：来源条目必须含 http(s):// 或数据文件名（.json/.csv/.xlsx），
自申报机构名标签一律不可信（宁缺勿错）。
"""

import pytest

from app.models.grad_intel import GradScorelineRecord
from app.services.grad_intel_service import scoreline_has_traceable_source


class TestSourcePredicate:
    @pytest.mark.parametrize(
        "sources,expected",
        [
            (["院校研究生院官网", "研招网"], False),
            (["研招网"], False),
            (["院校官网"], False),
            (None, False),
            ([], False),
            ("研招网", False),
            (["scorelines_real_data.json:2026-07-12"], True),
            (["https://gs.tsinghua.edu.cn/info/1173/9001.htm"], True),
            (["http://yz.xxx.edu.cn/zsjz.htm"], True),
            (["data.csv"], True),
            (["report.xlsx"], True),
            (["院校研究生院官网", "scorelines_real_data.json"], True),
        ],
    )
    def test_predicate(self, sources, expected):
        assert scoreline_has_traceable_source(sources) is expected


class TestListFilter:
    def _seed(self, db_session):
        db_session.add_all(
            [
                GradScorelineRecord(
                    university_name="清华大学",
                    major_name="软件工程",
                    degree_type="学硕",
                    year=2025,
                    total_score_line=380,
                    data_sources=["院校研究生院官网", "研招网"],
                ),
                GradScorelineRecord(
                    university_name="清华大学",
                    major_name="软件工程",
                    degree_type="学硕",
                    year=2024,
                    total_score_line=375,
                    data_sources=["scorelines_real_data.json:2026-07-12"],
                ),
            ]
        )
        db_session.commit()
        from app.core.cache import cache

        cache.clear()

    def test_list_only_returns_traceable(self, db_session):
        from app.services.grad_intel_service import list_scoreline_records

        self._seed(db_session)
        rows = list_scoreline_records(db_session, university_name="清华大学")
        assert len(rows) == 1
        assert rows[0].year == 2024

    def test_trend_only_returns_traceable(self, db_session):
        from app.services.grad_intel_service import get_scoreline_trend

        self._seed(db_session)
        trend = get_scoreline_trend(db_session, "清华大学", "软件工程")
        assert trend["years"] == [2024]
