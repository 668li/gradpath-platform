"""S1 主题相关度门禁测试（三角洲游戏视频混入考研 feed 事故的根治）。

覆盖 classify_topic_relevance 的判定策略与 transform 层拦截：
- 命中离题黑名单（游戏/娱乐）→ is_off_topic=True，即使含"心态/压力/坚持"等通用情绪词
- 命中平台领域词（考研/考公/考证/就业/在校）→ 相关并返回归属领域
- 完全无领域信号 → 判离题（无领域词），但 transform 层只对"明确离题黑名单"丢弃，
  "无领域词"存疑内容放行交给管理员审核（避免冷启动供给被过度缩减）
- 三角洲事故原文 → 离题并被打标（promote 层 is_off_topic=True，status 仍为 approved）
"""

from app.crawlers.research.transformer import ResearchTransformer, classify_topic_relevance


class TestClassifyTopicRelevance:
    def test_delta_force_game_video_is_offtopic(self):
        """事故原文：三角洲教学视频 → 命中离题词「三角洲」→ 离题。"""
        off, reason, domain = classify_topic_relevance(
            "【三角洲教学】针对普通玩家的单三心态调整及目标感教学",
            "游戏心态教学",
            ["三角洲", "FPS", "游戏"],
        )
        assert off is True
        assert "三角洲" in reason
        assert domain is None

    def test_game_mentality_words_overridden_by_blacklist(self):
        """含'心态'但命中游戏黑名单 → 仍判离题（黑名单优先于通用情绪词）。"""
        off, reason, _ = classify_topic_relevance(
            "王者荣耀心态调整教学，上分攻略",
            "",
            ["王者荣耀", "电竞"],
        )
        assert off is True
        assert "王者荣耀" in reason

    def test_kaoyan(self):
        off, reason, domain = classify_topic_relevance(
            "408 计算机考研上岸经验分享，数据结构与操作系统复习",
            "",
            ["考研", "408"],
        )
        assert off is False
        assert domain == "kaoyan"
        assert reason == ""

    def test_gongkao(self):
        off, _, domain = classify_topic_relevance("2026 国考行测申论复习规划，备考公务员")
        assert off is False
        assert domain == "gongkao"

    def test_certificate(self):
        off, _, domain = classify_topic_relevance("教师资格证考试备考指南")
        assert off is False
        assert domain == "certificate"

    def test_employment(self):
        off, _, domain = classify_topic_relevance("应届生求职面试经验分享，Offer 选择")
        assert off is False
        assert domain == "employment"

    def test_study(self):
        off, _, domain = classify_topic_relevance("大学转专业怎么选，绩点提升方法")
        assert off is False
        assert domain == "study"

    def test_kaoyan_with_mentality_not_offtopic(self):
        """考研语境下的'好心态' → 相关（未被黑名单误伤）。"""
        off, _, domain = classify_topic_relevance(
            "考研复习也要保持好心态，压力大怎么办",
            "",
            ["考研"],
        )
        assert off is False
        assert domain == "kaoyan"

    def test_no_signal_is_offtopic(self):
        """完全无领域信号 → 判离题。"""
        off, reason, domain = classify_topic_relevance("第一篇文章", "随便一段内容")
        assert off is True
        assert "未命中任何领域信号" in reason
        assert domain is None

    def test_empty_text(self):
        off, reason, _ = classify_topic_relevance("", "")
        assert off is True
        assert "无文本" in reason


class TestTransformTopicGate:
    def test_delta_force_dropped_at_transform(self):
        """transform_bilibili：三角洲离题 → 进审核队列前直接丢弃。"""
        items = [
            {
                "title": "【三角洲教学】针对普通玩家的单三心态调整及目标感教学",
                "summary": "",
                "content": "游戏心态教学",
                "bvid": "BVtest01",
                "source_url": "https://bilibili.com/video/BVtest01",
                "view_count": 100,
                "like_count": 5,
                "tags": ["三角洲", "FPS"],
                "source_platform": "bilibili",
            }
        ]
        assert ResearchTransformer.transform_bilibili(items) == []

    def test_no_signal_kept_at_transform(self):
        """无领域词但非黑名单 → transform 层放行（交给审核，避免误伤冷启动供给）。"""
        items = [
            {
                "title": "第一篇文章",
                "source_url": "https://example.com/a",
                "source_platform": "web",
            },
            {
                "title": "第二篇文章（重复链接）",
                "source_url": "https://example.com/a",
                "source_platform": "web",
            },
            {
                "title": "第三篇文章",
                "source_url": "https://example.com/b",
                "source_platform": "web",
            },
        ]
        payloads = ResearchTransformer.transform_web(items)
        # 放行 + URL 去重 → 2 条
        assert len(payloads) == 2

    def test_kaoyan_kept_at_transform(self):
        items = [
            {
                "title": "408 计算机考研上岸经验",
                "summary": "复习经验",
                "content": "数据结构与操作系统复习经验分享",
                "bvid": "BVtest02",
                "source_url": "https://bilibili.com/video/BVtest02",
                "view_count": 5000,
                "like_count": 300,
                "tags": ["考研", "408"],
                "source_platform": "bilibili",
            }
        ]
        payloads = ResearchTransformer.transform_bilibili(items)
        assert len(payloads) == 1