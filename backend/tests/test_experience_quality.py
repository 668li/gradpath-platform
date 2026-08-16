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
    extract_experience_meta_with_evidence,
    score_experience_item,
    score_experience_item_detailed,
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


class TestScoreExperienceDetailed:
    """Phase I：可解释打分（dimensions + reasons 供质量徽章 hover）。"""

    def test_dimensions_cover_five_dims_and_sum_to_score(self):
        detail = score_experience_item_detailed(
            title="408 计算机考研一战上岸经验",
            content="计划" + "具体到每天的刷题安排和错题复盘。" * 100,
            source_platform="bilibili",
            source_url="https://www.bilibili.com/video/BV1xxx",
            external_view_count=120_000,
            external_like_count=2000,
            is_promotion=False,
        )
        assert detail["score"] == 90
        assert detail["grade"] == "A"
        names = [d["name"] for d in detail["dimensions"]]
        assert names == ["trust", "completeness", "engagement", "traceable", "anti_promo"]
        # 各维度 points 之和 = score；max 之和 = 100
        assert sum(d["points"] for d in detail["dimensions"]) == detail["score"]
        assert sum(d["max"] for d in detail["dimensions"]) == 100
        # 每维都有可读说明
        assert all(d["reason"] for d in detail["dimensions"])

    def test_reasons_only_for_deducted_dims(self):
        """满分的维度不进 reasons；未拿满的维度逐条给出扣分说明。"""
        detail = score_experience_item_detailed(
            title="408 计算机考研一战上岸经验",
            content="计划" + "具体到每天的刷题安排和错题复盘。" * 100,
            source_platform="bilibili",
            source_url="https://www.bilibili.com/video/BV1xxx",
            external_view_count=120_000,
            external_like_count=2000,
            is_promotion=False,
        )
        # 90 分：trust 20/30、completeness 30/30、engagement 20/20、
        # traceable 10/10、anti_promo 10/10 → 只有来源可信度扣 10
        assert detail["reasons"] == ["来源可信度 20/30：社区来源（bilibili）"]

    def test_promotion_reason_lands_in_reasons(self):
        detail = score_experience_item_detailed(
            title="考研数学经验",
            content="笔记" + "刷题复盘方法。" * 200,
            source_platform="bilibili",
            source_url="https://www.bilibili.com/video/BV1yyy",
            external_view_count=120_000,
            is_promotion=True,
            promotion_reason="疑似软广: 加微信",
        )
        anti = next(d for d in detail["dimensions"] if d["name"] == "anti_promo")
        assert anti["points"] == 0
        assert any("反软广 0/10" in r and "加微信" in r for r in detail["reasons"])

    def test_detailed_matches_thin_wrapper(self):
        """score_experience_item 是 detailed 的薄壳：分数/等级完全一致。"""
        kwargs = dict(
            title="408 一战上岸清华大学经验",
            content="每天刷真题 + 错题复盘。" * 60,
            source_platform="zhihu",
            source_url="https://zhuanlan.zhihu.com/p/1",
            external_view_count=5000,
            external_like_count=200,
            is_promotion=False,
        )
        score, grade = score_experience_item(**kwargs)
        detail = score_experience_item_detailed(**kwargs)
        assert detail["score"] == score
        assert detail["grade"] == grade


class TestExtractExperienceMetaEvidence:
    """Phase I：结构化元信息证据链（evidence 原文片段 + confidence 置信度）。"""

    def test_positive_evidence_with_confidence(self):
        meta, evidence, confidence = extract_experience_meta_with_evidence(
            "408 一战上岸清华大学经验",
            "初试考了 380 分，每天刷真题，错题整理成笔记复盘",
            tags=["408"],
        )
        # meta 与旧版一致
        assert meta["school"] == "清华大学"
        assert meta["target_score"] == 380
        assert "真题" in meta["methods"]
        # evidence：命中字段都有原文片段（≤40 字）
        assert evidence["school"].startswith("原文「")
        assert evidence["target_score"].startswith("原文「")
        assert "380" in evidence["target_score"]
        assert evidence["subject"].startswith("原文含「")
        assert evidence["methods"].startswith("原文含「")
        # confidence：院校正则 0.85 / 分数正则 0.8 / 关键词命中 0.9
        assert confidence["school"] == 0.85
        assert confidence["target_score"] == 0.8
        assert confidence["subject"] == 0.9
        assert confidence["methods"] == 0.9

    def test_no_evidence_honest_empty(self):
        """无命中 → evidence/confidence 均为空字典（前端诚实降级）。"""
        meta, evidence, confidence = extract_experience_meta_with_evidence(
            "随便一段话", "没有干货内容"
        )
        assert evidence == {}
        assert confidence == {}
        assert meta["subject"] is None
        assert meta["school"] is None
        assert meta["methods"] == []
