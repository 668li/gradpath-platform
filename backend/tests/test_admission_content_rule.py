"""招生情报内容判定（admission_content_rule）测试。

正例/负例全部取自 2026-10-01 生产实测的 45 条 PENDING 真实标题——包括当时被临时词表
误判的三条（竞赛报名 / 十佳班长 / 督导全体会议），作为回归锁存在这里。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.admission_content_rule import classify_admission_item

# 真实标题（截断版，够判定用）：招生情报
ADMISSION_POSITIVES = [
    "山东大学2027年硕士研究生招生专业目录-山东大学研究生招生信息网",
    "山东大学2027年硕士生招生考试初试自命题科目考试大纲-山东大学研究生招生信息网",
    "山东大学2027年硕士研究生学制与学费标准-山东大学研究生招生信息网",
    "复旦大学2027年招收攻读硕士学位研究生章程",
    "复旦大学2027年各院系研究生招生咨询联系方式",
    "2027年山东科技大学报考点（3753）硕士研究生招生考试网上报名安排及注意事项",
    "山东科技大学2027年硕士研究生招生章程",
    "山东科技大学2027年硕士研究生初试科目参考书目",
    "关于报考少数民族高层次骨干人才计划硕士有关事项的说明-山东大学研究生招生信息网",
    "关于退役大学生士兵报考硕士研究生有关事项的说明-山东大学研究生招生信息网",
    # 关键负例反转：公示本身不是噪声，推免公示属招生情报
    "南开大学2027年各学院接收推荐免试研究生结果公示",
]

# 真实标题：校内行政 / 噪声 / 社区灌水（含 2026-10-01 误判三条）
ADMIN_NEGATIVES = [
    "[通知公告]【十佳】地学学院关于召开2025-2026学年“十佳班长”评选展示会的通知",
    "奖金最高10万+全程护航！第五届中国研究生网络安全创新大赛报名中！！",
    "开赛啦！第十二届中国研究生智慧城市技术与创意设计大赛",
    "竞赛报名！！“长沙银行杯”2026中国研究生创“芯”大赛·EDA精英挑战赛邀你与全国顶尖“芯”青年同台竞",
    "西安交大召开2026年秋季研究生督导全体会议",
    "主校区研究生校级公共课程“环境工程导论”考试安排",
    "同济医学院2026级研究生10月份课程考试通知",
    "关于开展青海海西州地震灾区研究生临时困难补助申请工作的通知",
    "研究生院（党委研究生工作部）国庆节假期值班安排",
    "关于2026级研究生新生图像补采的通知-湖南大学研究生院",
    "关于2026-2027学年秋学期研究生课程退（改、补）选的通知",
    "论文送审平台反馈评阅意见份数统计表（截至2026年9月30日8:45）-天津大学研究生院官网",
    "【学位申请】关于2026年下半年申请博士学位人员资格审查结果的公示（动态更新）",
]


class TestAdmissionPositives:
    @pytest.mark.parametrize("title", ADMISSION_POSITIVES)
    def test_real_admission_titles_pass(self, title):
        is_admission, reason = classify_admission_item(title)
        assert is_admission is True, f"误杀招生情报：{title}（{reason}）"
        assert "招生锚点" in reason

    def test_push_exemption_public_notice_is_admission(self):
        """推免结果公示含"公示"，不得被当成校内行政误杀。"""
        is_admission, _ = classify_admission_item("南开大学2027年各学院接收推荐免试研究生结果公示")
        assert is_admission is True

    def test_content_participates_when_title_does_not(self):
        is_admission, _ = classify_admission_item(
            "通知", content="我校2027年硕士研究生招生章程见附件。"
        )
        assert is_admission is True


class TestAdminNegatives:
    @pytest.mark.parametrize("title", ADMIN_NEGATIVES)
    def test_real_admin_titles_blocked(self, title):
        is_admission, reason = classify_admission_item(title)
        assert is_admission is False, f"漏过校内行政：{title}"

    @pytest.mark.parametrize(
        "title",
        [
            "[通知公告]【十佳】地学学院关于召开2025-2026学年“十佳班长”评选展示会的通知",
            "竞赛报名！！“长沙银行杯”2026中国研究生创“芯”大赛·EDA精英挑战赛邀你与全国顶尖“芯”青年同台竞",
            "西安交大召开2026年秋季研究生督导全体会议",
        ],
    )
    def test_three_measured_false_positives_now_blocked(self, title):
        """2026-10-01 临时词表把这三条误判进招生桶；本规则必须挡住。"""
        is_admission, _ = classify_admission_item(title)
        assert is_admission is False

    def test_noise_reason_is_reported(self):
        """被排除词命中时，理由须指名排除词（人工复核要看这个）。"""
        _ok, reason = classify_admission_item("竞赛报名通知")
        assert "排除词" in reason

    def test_no_anchor_reason_is_reported(self):
        _ok, reason = classify_admission_item("关于实验室门禁改造的通知")
        assert "未命中" in reason

    def test_community_spam_blocked(self):
        for title in (
            "猫咪底层代码到底是什么，为什么总是那么神经？",
            "瓶装水在开封后，多久会变质？",
        ):
            is_admission, _ = classify_admission_item(title)
            assert is_admission is False


class TestEdgeCases:
    def test_empty_input_is_not_admission(self):
        assert classify_admission_item("")[0] is False
        assert classify_admission_item("", "")[0] is False

    def test_none_input_does_not_raise(self):
        assert classify_admission_item(None, None)[0] is False  # type: ignore[arg-type]

    def test_bare_baoming_is_not_an_anchor(self):
        """裸"报名"不作锚点——它是 25% 误判的主因，只认报名点/网上报名。"""
        assert classify_admission_item("创业大赛报名通知")[0] is False
        assert classify_admission_item("研究生招生网上报名安排")[0] is True

    def test_noise_wins_over_anchor(self):
        """同时命中锚点与排除词时，排除优先（宁可漏放交人工，不放行政通知）。"""
        is_admission, reason = classify_admission_item("研究生招生竞赛评选通知")
        assert is_admission is False
        assert "排除词" in reason
