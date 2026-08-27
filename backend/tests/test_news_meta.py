# backend/tests/test_news_meta.py
"""考研资讯结构化元信息抽取测试（Phase G 决策数据卡）。

覆盖 extract_news_structured_meta 的三类规则：
- 招生人数（拟招/计划招 + 数字+人）
- 考试科目（初试科目：101思想政治理论...）
- 参考书目（《书名》）
以及抽不到时的诚实降级（None / []）。
"""

from app.crawlers.research.news_meta import (
    _extract_enrollment_count,
    _extract_exam_subjects,
    _extract_reference_books,
    extract_news_structured_meta,
    extract_news_structured_meta_with_evidence,
)


class TestEnrollmentCount:
    def test_plan_enroll(self):
        assert _extract_enrollment_count("2026招生简章", "计算机学院拟招收 120 人") == 120

    def test_enroll_without_spaces(self):
        assert _extract_enrollment_count("招生计划", "计划招生80人，其中推免20人") == 80

    def test_enroll_in_title(self):
        assert _extract_enrollment_count("拟录取 45 人左右", "名单见附件") == 45

    def test_enroll_with_modifier(self):
        assert _extract_enrollment_count("扩招公告", "今年新增 300 个名额") == 300

    def test_no_enroll_returns_none(self):
        assert _extract_enrollment_count("复试线公布", "各院校陆续公布分数线") is None

    def test_unreasonable_number_rejected(self):
        """超出合理性护栏（>9999 或 0）→ None，不编造。"""
        assert _extract_enrollment_count("公告", "拟招 99999 人") is None
        assert _extract_enrollment_count("公告", "拟招 0 人") is None


class TestExamSubjects:
    def test_code_name_subjects(self):
        """初试科目后接 ①代码+名称 → 提取名称部分。"""
        subjects = _extract_exam_subjects(
            "2026考研大纲",
            "初试科目：①101思想政治理论②201英语一③301数学一",
        )
        assert "思想政治理论" in subjects
        assert "英语一" in subjects
        assert "数学一" in subjects

    def test_plain_name_subjects(self):
        """无代码科目名（专业课名称）也能提取。"""
        subjects = _extract_exam_subjects(
            "招生目录",
            "考试科目：数据结构、计算机组成原理",
        )
        assert "数据结构" in subjects
        assert "计算机组成原理" in subjects

    def test_stops_at_sentence_boundary(self):
        """科目段在句号处截断，不吞掉后续正文。"""
        subjects = _extract_exam_subjects(
            "复试通知",
            "初试科目：英语一、数学二。复试包括笔试面试。",
        )
        assert "英语一" in subjects
        assert "数学二" in subjects
        assert all(s != "复试" for s in subjects)

    def test_no_subjects_returns_empty(self):
        assert _extract_exam_subjects("调剂公告", "名额有限") == []

    def test_title_announcement_not_subjects(self):
        """标题里的"初试科目调整公告"是公告名不是科目列表，不误抓整句。"""
        subjects = _extract_exam_subjects(
            "山东师范大学2027年硕士招生考试部分专业初试科目调整公告(一)",
            "详见附件",
        )
        assert subjects == []

    def test_code_subjects_without_colon(self):
        """无冒号但以科目代码开头的指代（专业课①408...）仍可抽取。"""
        subjects = _extract_exam_subjects(
            "2027年华中农业大学专业课①408计算机学科专业基础",
            "考试大纲见附件",
        )
        assert "计算机学科专业基础" in subjects


class TestReferenceBooks:
    def test_book_title_marks(self):
        books = _extract_reference_books(
            "参考书目",
            "参考书为《数据结构（C语言版）》与《计算机网络》",
        )
        assert "数据结构（C语言版）" in books
        assert "计算机网络" in books

    def test_duplicates_deduped(self):
        books = _extract_reference_books(
            "书单",
            "《高等数学》上下册《高等数学》",
        )
        assert books.count("高等数学") == 1

    def test_no_books_returns_empty(self):
        assert _extract_reference_books("复试线", "无参考书目要求") == []

    def test_subject_code_book_marks_not_books(self):
        """440《新闻与传播专业基础》是科目指代不是参考书。"""
        books = _extract_reference_books(
            "2027年华中农业大学440《新闻与传播专业基础》硕士自命题",
            "参考书为《数据结构（C语言版）》",
        )
        assert "新闻与传播专业基础" not in books
        assert "数据结构（C语言版）" in books


class TestExtractStructuredMeta:
    def test_full_news_card(self):
        """三类字段同时抽取 → 决策数据卡完整。"""
        meta = extract_news_structured_meta(
            "2026年XX大学计算机考研招生简章",
            "计算机学院拟招收 120 人。初试科目：①101思想政治理论②201英语一"
            "③301数学一④408计算机学科专业基础。参考书：《数据结构（C语言版）》"
            "《计算机网络》。",
        )
        assert meta["enrollment_count"] == 120
        assert "思想政治理论" in meta["exam_subjects"]
        assert (
            "408计算机学科专业基础" in meta["exam_subjects"]
            or "计算机学科专业基础" in meta["exam_subjects"]
        )
        assert "数据结构（C语言版）" in meta["reference_books"]

    def test_no_signal_degrades_honestly(self):
        """抽不到 → None / []，诚实降级不编造。"""
        meta = extract_news_structured_meta("普通资讯", "无结构化信息")
        assert meta["enrollment_count"] is None
        assert meta["exam_subjects"] == []
        assert meta["reference_books"] == []


class TestEvidenceChain:
    """Phase I：资讯证据链（evidence 原文片段 + confidence + effective_year）。"""

    def test_full_evidence_and_year(self):
        meta, evidence, confidence, effective_year = extract_news_structured_meta_with_evidence(
            "2026年XX大学计算机考研招生简章",
            "计算机学院拟招收 120 人。初试科目：①101思想政治理论②201英语一。"
            "参考书：《数据结构（C语言版）》。",
        )
        # meta 与旧版一致
        assert meta["enrollment_count"] == 120
        assert "思想政治理论" in meta["exam_subjects"]
        # effective_year：招/录/名额上下文中的 20xx 年
        assert effective_year == 2026
        # evidence：命中字段都有原文片段（≤40 字）
        assert evidence["enrollment_count"].startswith("原文「")
        assert "120" in evidence["enrollment_count"]
        assert evidence["effective_year"].startswith("原文「")
        assert "2026" in evidence["effective_year"]
        # confidence：人数 0.8 / 科目 0.7 / 参考书 0.85 / 年份 0.8
        assert confidence["enrollment_count"] == 0.8
        assert confidence["exam_subjects"] == 0.7
        assert confidence["reference_books"] == 0.85
        assert confidence["effective_year"] == 0.8

    def test_no_signal_honest_empty(self):
        meta, evidence, confidence, effective_year = extract_news_structured_meta_with_evidence(
            "普通资讯", "无结构化信息"
        )
        assert evidence == {}
        assert confidence == {}
        assert effective_year is None
        assert meta["enrollment_count"] is None

    def test_thin_wrapper_consistent(self):
        """extract_news_structured_meta 是证据链版薄壳：meta 完全一致。"""
        title = "2026年XX大学计算机考研招生简章"
        content = "计算机学院拟招收 120 人。参考书：《数据结构（C语言版）》。"
        plain = extract_news_structured_meta(title, content)
        meta, _, _, _ = extract_news_structured_meta_with_evidence(title, content)
        assert meta == plain


class TestEffectiveYear:
    """数据年份抽取 + 年号护栏（仅招/录/名额/简章/统考/调剂上下文才算）。"""

    def test_year_zhang_sheng_jian_zhang(self):
        _, _, _, year = extract_news_structured_meta_with_evidence("2026年招生简章发布", "详见附件")
        assert year == 2026

    def test_year_nizhaosheng(self):
        _, _, _, year = extract_news_structured_meta_with_evidence(
            "招生公告", "2026 年拟招收 120 人"
        )
        assert year == 2026

    def test_year_luqu(self):
        _, _, _, year = extract_news_structured_meta_with_evidence(
            "拟录取名单", "2026年拟录取 45 人"
        )
        assert year == 2026

    def test_bare_year_without_context_rejected(self):
        """无招/录/名额等上下文 → 年号护栏拦截，不误标数据年份。"""
        _, _, _, year = extract_news_structured_meta_with_evidence(
            "复试线公布", "截至2026年3月陆续公布"
        )
        assert year is None

    def test_year_in_date_phrase_rejected(self):
        """「2025年1月1日调剂系统」中 年 后紧跟日期而非招/录 → 不匹配。"""
        _, _, _, year = extract_news_structured_meta_with_evidence(
            "调剂公告", "2025年1月1日调剂系统开放"
        )
        assert year is None

    def test_no_year_returns_none(self):
        _, _, _, year = extract_news_structured_meta_with_evidence(
            "复试线公布", "各院校陆续公布分数线，无年份信息"
        )
        assert year is None
