"""爬虫合规白名单（B1 堵旁路）。

合规红线（数据真实 + 仅人工确认入库）：外部数据一律先写 PENDING 审核队列
（t_external_research_item + t_review_queue_item），由管理员在 admin 端
人工确认后才落业务表。因此只允许"store() 走 store_research_items"的爬虫
通过任何触发入口（admin API /run、/schedules、CLI）执行。

直写业务表的旧爬虫（假数据 / 绕过人工审核）一律拒绝，杜绝旁路入库。
新增合规爬虫时需同步加入名单，并保证其 store() 只走 store_research_items。
"""
from __future__ import annotations

ALLOWED_CRAWLER_SOURCES: frozenset[str] = frozenset({
    "real_data",              # grad：研招网/高校官网/学位网 → PENDING 队列
    "yanzhao",                # grad：招生简章预置数据 → PENDING 队列（B1 改造后）
    "yanzhao_program",        # grad：专业目录预置数据 → PENDING 队列（B1 改造后）
    "bilibili_research",      # research：B站考研视频 → PENDING 队列
    "web_article_research",   # research：网页文章 → PENDING 队列
    "rss_news_research",      # research：RSS 新闻 → PENDING 队列（注册名，勿写模块文件名）
})


def is_allowed_crawler(source_name: str) -> bool:
    """判断爬虫是否在合规白名单内（未命中一律视为旁路，拒绝执行）。"""
    return source_name in ALLOWED_CRAWLER_SOURCES
