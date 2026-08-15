# backend/tests/test_experience_quality.py
"""经验贴提纯规则测试（Phase G 经验闭环核心）。

覆盖：
- score_experience_item 五维打分（来源可信度/完整度/互动/可溯源/反软广）与 A-D 分级边界
- detect_promotion 软广/引流检测正反例（命中标注、置信度、无证据上浮）
- extract_experience_meta 结构化抽取（学科/阶段/院校/目标分/方法/适用人群）
"""
import pytest

from app.crawlers.research.experience_quality import (
    detect_promotion,
    extract_experience_meta,
    score_experience_item,
)


class TestScoreExperience:
    """五维打分与分级边界。"""

    def test_full_quality_community_post_is_A(self):
        """B站社区 + 千字长文 + 10w 播放 + 可溯源 + 非软广 → 90 分 A。"""
        score, grade = score_experience_item(
            title="408 计算机考研一战上岸经验",
            content="计划" + "具体到每天的刷题安排和错题复盘。" * 100,  # 1500+ 字
            source_platform="bilibili",
            source_url="https://www.bilibili.com/video/BV1xxx",
            external_view_count=120_000,
            external_like_count=2000,
            is_promotion=False,
        )
        # 20 + 30 + 20 + 10 + 10 = 90
        assert score == 90
        assert grade == "A"

    def test_promotion_knocks_anti_promo_dimension(self):
        """软广标注 → 反软广维度 0 分，但整体仍可能 A（标注不剔除）。"""
        score, grade = score_experience_item(
            title="考研数学经验",
            content="笔记" + "刷题复盘方法。" * 200,  # 1200+ 字
            source_platform="bilibili",
            source_url="https://www.bilibili.com/video/BV1yyy",
            external_view_count=120_000,  # ≥10w → 互动满分 20
            is_promotion=True,
        )
        # 20 + 30 + 20 + 10 + 0(反软广) = 80
        assert score == 80
        assert grade == "A"

    def test_short_content_scores_low(self):
        """只有标题无正文、无互动 → 分数低（内容完整度/互动 0）。"""
        score, _ = score_experience_item(
            title="考研复试经验",
            content="",
            source_platform="user",
            source_url="",
            external_view_count=0,
        )
        # 15(user) + 0 + 0 + 0(无url) + 10 = 25 → D
        assert score == 25

    def test_official_source_gets_trust_boost(self):
        """官方域名来源可信度更高。"""
        score, grade = score_experience_item(
            title="XX大学2026考研复试安排",
            content="官方公告内容" * 200,  # 1200 字 → 完整度 30
            source_platform="bilibili",
            source_url="https://grad.xxx.edu.cn/news/1",
            external_view_count=0,
        )
        # 25 + 30 + 0 + 10 + 10 = 75 → A 边界
        assert score == 75
        assert grade == "A"

    def test_grade_boundaries(self):
        """A≥75 / B≥55 / C≥35，其余 D — 用确定性组合验证边界。"""
        # 74 → B（20 bilibili + 24 完整度500字 + 10 互动1k + 10 溯源 + 10 反软广）
        _, g74 = score_experience_item(
            title="考研英语经验贴", content="单词记忆方法" * 40,  # 约 600 字
            source_platform="bilibili", source_url="https://bilibili.com/v/1",
            external_view_count=1500,
        )
        assert g74 == "B"
        # 54 → C（20 + 4 短内容 + 10 互动1k + 10 + 10）
        _, g54 = score_experience_item(
            title="考研英语经验贴", content="单词要反复背",
            source_platform="bilibili", source_url="https://bilibili.com/v/1",
            external_view_count=1500,
        )
        assert g54 == "C"
        # 25 → D（15 user + 0 完整 + 0 互动 + 0 溯源 + 10 反软广）
        _, g25 = score_experience_item(
            title="随便一句", content="",
            source_platform="user", source_url="",
        )
        assert g25 == "D"

    def test_score_clamped_to_100(self):
        score, grade = score_experience_item(
            title="考研复试经验", content="内容" * 500,
            source_platform="bilibili", source_url="https://bilibili.com/v/1",
            external_view_count=999_999, external_like_count=9999,
        )
        assert score <= 100
        assert grade == "A"


class TestDetectPromotion:
    """软广/引流检测正反例。"""

    def test_lead_gen_keyword_flags(self):
        """命中引流词（加微信/私信/领资料）→ 标注。"""
        is_promo, conf, reason = detect_promotion(
            "二战考研互助群，加我vx领资料",
            "加微信进群，免费领取数学真题资料包",
        )
        assert is_promo is True
        assert 0.5 < conf <= 0.95
        assert reason.startswith("疑似软广:")

    def test_strong_marketing_keyword(self):
        """命中强营销词（包过/保录取）→ 高置信标注。"""
        is_promo, conf, _ = detect_promotion(
            "考研保过班，不过退费",
            "内部资料+押题，名额有限，定金预留",
        )
        assert is_promo is True
        assert conf >= 0.6

    def test_clean_post_not_flagged(self):
        """正常经验分享（无任何引流/售卖词）→ 不标注。"""
        is_promo, conf, reason = detect_promotion(
            "408 一战上岸北京理工大学经验",
            "我每天刷 4 小时真题，把错题整理成笔记反复复盘，最后初试考了 380 分",
        )
        assert is_promo is False
        assert conf == 0.0
        assert reason == ""

    def test_evidence_reduces_confidence(self):
        """带院校/分数证据的推广贴置信度低于无证据纯引流号。"""
        _, conf_with_evidence, _ = detect_promotion(
            "上岸清华大学经验（含领资料入口）",
            "我最终考了 390 分，加微信领我的笔记",
        )
        _, conf_without_evidence, _ = detect_promotion(
            "加我私信领资料",
            "免费领考研资料，进群",
        )
        assert conf_without_evidence > conf_with_evidence


class TestExtractExperienceMeta:
    """结构化元信息抽取。"""

    def test_subject_and_stage(self):
        meta = extract_experience_meta(
            "408 计算机考研复试经验分享",
            "复试流程详细记录",
        )
        assert meta["subject"] == "408"
        assert meta["stage"] == "复试"

    def test_school_and_target_score(self):
        meta = extract_experience_meta(
            "一战上岸清华大学",
            "初试考了 380 分，复试顺利通过",
        )
        assert meta["school"] == "清华大学"
        assert meta["target_score"] == 380

    def test_methods_and_audience(self):
        meta = extract_experience_meta(
            "二战考研时间规划",
            "我按照错题复盘 + 思维导图的方法，每天固定时间表刷真题",
        )
        assert meta["audience"] == "二战"
        assert "复盘" in meta["methods"]
        assert "真题" in meta["methods"]

    def test_no_evidence_returns_none_fields(self):
        meta = extract_experience_meta("随便一段话", "没有干货内容")
        assert meta["subject"] is None
        assert meta["school"] is None
        assert meta["target_score"] is None
        assert meta["methods"] == []
