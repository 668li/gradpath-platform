# backend/tests/test_news_meta.py
"""考研资讯结构化元信息抽取测试（Phase G 决策数据卡）。

覆盖 extract_news_structured_meta 的三类规则：
- 招生人数（拟招/计划招 + 数字+人）
- 考试科目（初试科目：101思想政治理论...）
- 参考书目（《书名》）
以及抽不到时的诚实降级（None / []）。
"""
import pytest

from app.crawlers.research.news_meta import (
    _extract_enrollment_count,
    _extract_exam_subjects,
    _extract_reference_books,
    extract_news_structured_meta,
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
        assert all("复试" != s for s in subjects)

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
        assert "408计算机学科专业基础" in meta["exam_subjects"] or "计算机学科专业基础" in meta["exam_subjects"]
        assert "数据结构（C语言版）" in meta["reference_books"]

    def test_no_signal_degrades_honestly(self):
        """抽不到 → None / []，诚实降级不编造。"""
        meta = extract_news_structured_meta("普通资讯", "无结构化信息")
        assert meta["enrollment_count"] is None
        assert meta["exam_subjects"] == []
        assert meta["reference_books"] == []
