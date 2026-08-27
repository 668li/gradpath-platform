# backend/tests/test_dedup.py
"""资讯相似度去重（Phase A1）单元测试 — SimHash 汉明距离边界 + URL 归一化。

覆盖：
- compute_simhash：相同文本相同 hash / 空文本 0 / 确定性
- is_similar：汉明距离 <= 3 判相似，>3 判不相似
- find_similar：在 hash 列表中的命中/未命中
- normalize_url：tracking 参数剔除 / 协议与 www 归一 / 尾斜杠
"""

from app.crawlers.research.dedup import (
    compute_simhash,
    find_similar,
    hamming_distance,
    is_similar,
    normalize_url,
)

# 与 store_research_items 一致：simhash 比对文本 = title + 正文前 500 字。
# 短标题（仅几个 bigram）在 64-bit simhash 下噪声大（一字之差可达 10+ 位），
# 而真实采集比对的是标题+正文（几百字），近重复距离可压到 <=3、无关文本 30+，
# 故测试 fixture 用贴近真实管线长度的文本。
_BODY = (
    "网上报名时间为2025年10月15日至10月28日，每天9:00-22:00。"
    "考生应在规定时间内登录研招网报名系统，按要求填写个人信息、报考院校及专业。"
    "报名期间可自行修改网上报名信息，逾期不再补报。"
    "初试时间为2025年12月20日至21日，上午8:30-11:30思想政治理论，下午14:00-17:00外国语。"
    "考生应提前打印准考证。"
)
_OTHER_BODY = "某高校公布 2026 年博士研究生拟录取名单公示，公示期为 7 个工作日。"


class TestComputeSimhash:
    def test_same_text_same_hash(self):
        text = "2026 年全国硕士研究生招生考试报名时间公布"
        assert compute_simhash(text) == compute_simhash(text)

    def test_deterministic_across_calls(self):
        # sha256 确定性哈希，不依赖 hash 随机化
        a = compute_simhash("考研报名 10 月启动")
        b = compute_simhash("考研报名 10 月启动")
        assert a == b and a != 0

    def test_empty_text_returns_zero(self):
        assert compute_simhash("") == 0
        assert compute_simhash(None) == 0

    def test_self_hamming_zero(self):
        h = compute_simhash("某大学 2026 考研招生简章发布")
        assert hamming_distance(h, h) == 0


class TestIsSimilar:
    def test_near_duplicate_similar(self):
        # 同一事件不同转载：标题一字之差（发布/公布）+ 正文一致 → 判相似
        a = f"某大学 2026 考研招生简章发布 {_BODY}"
        b = f"某大学 2026 考研招生简章公布 {_BODY}"
        assert is_similar(a, b)

    def test_unrelated_text_not_similar(self):
        a = f"2026 考研网上报名时间公布 {_BODY}"
        b = f"某高校公布 2026 年博士研究生拟录取名单公示 {_OTHER_BODY}"
        assert not is_similar(a, b)

    def test_empty_text_never_similar(self):
        assert not is_similar("", "任意内容")
        assert not is_similar("内容", "")

    def test_threshold_boundary(self):
        # 显式阈值边界：阈值 0 时仅完全相同文本相似
        text = f"2026 考研大纲发布 {_BODY}"
        assert is_similar(text, text, threshold=0)
        # 阈值放大后更多文本被判相似（宽松阈值语义：>= 即命中）
        h = compute_simhash(text)
        assert find_similar(f"2026 考研大纲公布 {_BODY}", [h], threshold=10) is not None
        assert find_similar(f"今天天气不错适合跑步 {_OTHER_BODY}", [h], threshold=10) is None


class TestFindSimilar:
    def test_hits_existing(self):
        h = compute_simhash(f"2026 考研初试时间为 12 月下旬 {_BODY}")
        found = find_similar(f"2026 考研初试 12 月下旬举行 {_BODY}", [h])
        assert found == h

    def test_miss_when_far(self):
        h = compute_simhash(f"2026 考研初试时间为 12 月下旬 {_BODY}")
        assert find_similar(f"考研政治选择题每日一练更新 {_OTHER_BODY}", [h]) is None

    def test_empty_hashes_returns_none(self):
        assert find_similar("任何文本", []) is None


class TestNormalizeUrl:
    def test_strips_tracking_params(self):
        url = "https://news.eol.cn/a.html?utm_source=weibo&id=123&spm=abc&from=group"
        assert normalize_url(url) == "https://news.eol.cn/a.html?id=123"

    def test_protocol_and_www_normalized(self):
        assert normalize_url("http://www.eol.cn/kaoyan/") == "https://eol.cn/kaoyan"

    def test_keeps_meaningful_query(self):
        # 非 tracking 参数保留，顺序与原始 query 一致（parse_qsl 保留顺序，不排序）
        assert normalize_url("https://a.cn/x?b=2&a=1") == "https://a.cn/x?b=2&a=1"

    def test_same_page_different_tracking_same_normalized(self):
        u1 = "https://eol.cn/kaoyan/news.shtml?utm_campaign=sp"
        u2 = "http://www.eol.cn/kaoyan/news.shtml?from=share"
        assert normalize_url(u1) == normalize_url(u2)

    def test_empty_and_bare(self):
        assert normalize_url("") == ""
        assert normalize_url("eol.cn/kaoyan") == "https://eol.cn/kaoyan"
