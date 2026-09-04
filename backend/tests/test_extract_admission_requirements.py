# backend/tests/test_extract_admission_requirements.py
"""出身硬门槛条款提取器回归测试（A2 工具，scripts/extract_admission_requirements.py）。

语义映射（2026-09-02 用户拍板）：拒绝→severe；有条件→moderate；标准措辞→none；
高职满年限→none；复试加试（教育部统一规定）不算该校态度；调剂硬/软→severe/moderate。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.extract_admission_requirements import analyze, extract_eqv, extract_tiaoshi


class TestEqvReject:
    def test_school_rejects(self):
        r = extract_eqv("我校部分专业不招收同等学力考生。")
        assert r and r["tier"] == "severe"

    def test_candidate_forbidden(self):
        r = extract_eqv("同等学力考生不得报考我校医学类专业。")
        assert r and r["tier"] == "severe"


class TestEqvCondition:
    def test_explicit_extra_requirements(self):
        r = extract_eqv("同等学力考生须满足以下条件：以第一作者身份发表核心期刊论文。")
        assert r and r["tier"] == "moderate"

    def test_thu_style_upgrade(self):
        """标准措辞前 160 字内出现"必须同时满足条件"→ 升级 moderate（清华 2026 实例）。"""
        text = (
            "国家承认学历的本科结业生，但必须同时满足以下条件："
            "a.修完本科主干课程；b.通过国家英语六级；c.以第一作者发表一篇核心期刊论文，"
            "并按本科毕业同等学力身份报考。"
        )
        r = extract_eqv(text)
        assert r and r["tier"] == "moderate"


class TestEqvStandard:
    def test_standard_wording(self):
        r = extract_eqv("获得国家承认的高职高专毕业学历后满2年，按本科毕业同等学力身份报考。")
        assert r and r["tier"] == "none"
        assert r["label"] == "按本科毕业同等学力身份报考"

    def test_retest_addition_excluded(self):
        """复试加试属教育部统一规定，不得升级为 moderate（UESTC/SDUT 均为标准措辞+加试）。"""
        text = (
            "同等学力考生复试时须加试两门与报考专业相关的本科主干课程。"
            "符合条件者可按本科毕业同等学力身份报考。"
        )
        r = extract_eqv(text)
        assert r and r["tier"] == "none"

    def test_reject_wins_over_standard(self):
        """同一文本同时含拒绝与标准措辞时，拒绝优先（提取顺序保证）。"""
        text = "部分专业不招收同等学力考生，其余专业按同等学力身份报考。"
        r = extract_eqv(text)
        assert r and r["tier"] == "severe"


class TestEqvHigherVoc:
    def test_mojin_recognized(self):
        r = extract_eqv("获得国家承认的高职高专毕业学历后，达到与大学本科毕业生同等学力。")
        assert r and r["tier"] == "none" and r["source"] == "eqv_higher_voc"

    def test_zhuanke_two_years_arabic_numeral(self):
        """"专科毕业满2年"（阿拉伯数字）须命中——回测发现的正则缺口。"""
        r = extract_eqv("专科毕业满2年者可报考。")
        assert r and r["tier"] == "none"

    def test_zhuanke_two_years_chinese_numeral(self):
        r = extract_eqv("专科毕业满两年者可报考。")
        assert r and r["tier"] == "none"


class TestTiaoshi:
    def test_hard_restriction(self):
        r = extract_tiaoshi("调剂仅限双一流高校本科毕业生。")
        assert r and r["tier"] == "severe"

    def test_soft_preference(self):
        r = extract_tiaoshi("接收调剂时，双一流高校毕业考生优先考虑。")
        assert r and r["tier"] == "moderate"

    def test_generic_no_match(self):
        assert extract_tiaoshi("调剂政策以国家规定为准。") is None


class TestAnalyze:
    def test_html_cross_tag_phrase(self):
        """HTML 标签切断关键词时仍可命中（strip+中文空白折叠）。"""
        html = "<p>符合条件者可按本科毕业</p><p>同等学力身份报考。</p>"
        r = analyze(html)
        assert r["clause_count"] == 1 and r["clauses"][0]["tier"] == "none"

    def test_both_sources(self):
        text = "按同等学力身份报考。调剂仅限211高校本科毕业生。"
        r = analyze(text)
        assert r["clause_count"] == 2
        assert {c["source"] for c in r["clauses"]} == {"eqv", "tiaoshi"}

    def test_neutral_school(self):
        r = analyze("我校热忱欢迎广大考生报考。")
        assert r == {"clause_count": 0, "clauses": []}

    def test_clause_quote_contains_match(self):
        r = analyze("我校不招收同等学力考生。")
        assert "不招收同等学力" in r["clauses"][0]["quote"]
