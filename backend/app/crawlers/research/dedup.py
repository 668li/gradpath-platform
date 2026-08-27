"""资讯相似度去重 — 轻量 SimHash（无重依赖）。

考研信息差产品的第一原则是"同一信息只保留最优一条"：
同一事件（如"2026 考研报名时间公布"）会被多个站点转载，source_url 不同，
精确 URL 去重拦不住 → 用 SimHash 对标题+摘要做相似判定，汉明距离 <= 3 视为重复。

- 64-bit SimHash，token = 中文 char bigram + 英文单词/数字（sha256 确定性哈希，
  不依赖 Python 内置 hash 随机化）
- hamming_distance 汉明距离
- normalize_url：去 http/https 差异、www 前缀、tracking 参数（utm_*/spm/from 等）
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# URL 归一化时要剔除的 tracking 参数（知乎/微博/门户常见）
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "spm",
    "from",
    "ref",
    "share_token",
    "share_source",
    "wfr",
}

# 英文单词/数字（含版本号、年份、学科代码如 408）
_TOKEN_RE = re.compile(r"[a-z0-9]+")
# 连续中文字符段
_HANZI_RE = re.compile(r"[\u4e00-\u9fff]+")

# 相似判定阈值（外部调研结论：标题+摘要级文本 汉明距离 <= 3 判定重复）
SIMILARITY_THRESHOLD = 3


def _tokens(text: str) -> list[str]:
    """切分文本为特征 token：英文单词/数字 + 中文 char bigram。"""
    lowered = text.lower()
    tokens = _TOKEN_RE.findall(lowered)
    for hz in _HANZI_RE.findall(lowered):
        if len(hz) == 1:
            tokens.append(hz)
        else:
            tokens.extend(hz[i : i + 2] for i in range(len(hz) - 1))
    return tokens


def compute_simhash(text: str) -> int:
    """计算 64-bit SimHash；空文本返回 0（调用方应跳过空文本比对）。"""
    tokens = _tokens(text or "")
    if not tokens:
        return 0
    v = [0] * 64
    for token in tokens:
        h = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
        for i in range(64):
            if (h >> (63 - i)) & 1:
                v[i] += 1
            else:
                v[i] -= 1
    result = 0
    for i in range(64):
        if v[i] > 0:
            result |= 1 << (63 - i)
    return result


def hamming_distance(a: int, b: int) -> int:
    """计算两个 64-bit SimHash 的汉明距离（不同 bit 数）。"""
    return (a ^ b).bit_count()


def is_similar(text_a: str, text_b: str, threshold: int = SIMILARITY_THRESHOLD) -> bool:
    """两段文本是否相似（SimHash 汉明距离 <= threshold）。空文本永远不相似。"""
    ha, hb = compute_simhash(text_a), compute_simhash(text_b)
    if ha == 0 or hb == 0:
        return False
    return hamming_distance(ha, hb) <= threshold


def find_similar(
    text: str,
    hashes: list[int],
    threshold: int = SIMILARITY_THRESHOLD,
) -> int | None:
    """在已有 simhash 列表中找与 text 相似的第一条，返回其 simhash；无则 None。

    Args:
        text: 待判定文本（标题+摘要）
        hashes: 库内已有条目的 simhash 列表
        threshold: 汉明距离阈值
    """
    h = compute_simhash(text)
    if h == 0:
        return None
    for existing in hashes:
        if existing != 0 and hamming_distance(h, existing) <= threshold:
            return existing
    return None


def normalize_url(url: str) -> str:
    """URL 归一化：http/https 统一为 https、去 www.、去 tracking 参数、去尾斜杠。

    归一化结果用于跨站点转载时的近似去重（同正文不同 query 视为同一 URL）。
    """
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    try:
        parsed = urlsplit(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        # 去掉 tracking 参数（保留有意义 query）
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query = [(k, v) for k, v in query if k.lower() not in TRACKING_PARAMS]
        query_str = urlencode(query)
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit(("https", host, path, query_str, ""))
    except ValueError:
        return url
