"""调研数据清洗、去重、结构化转换器。

将 B站视频、网页文章、RSS 资讯等原始 crawler 输出转换为可写入数据库的 payload。
"""

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.crawlers.research.quality import score_item

logger = logging.getLogger(__name__)

# 系统用户 ID，用于发布种子/系统内容
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# 广告/引流关键词（命中即丢弃）
AD_KEYWORDS = [
    "加微信",
    "领资料",
    "私信",
    "进群",
    "二维码",
    "优惠",
    "限时",
]

# 学科关键词
SUBJECT_KEYWORDS = [
    "408",
    "数据结构",
    "计算机组成原理",
    "操作系统",
    "计算机网络",
    "数学",
    "英语",
    "政治",
    "计算机",
    "金融",
    "法学",
    "教育学",
    "医学",
]

# 阶段关键词
STAGE_KEYWORDS = [
    "择校",
    "选校",
    "备考",
    "复习",
    "初试",
    "复试",
    "调剂",
    "上岸",
    "二战",
]

# 分类映射：按标题关键词归类
# Phase H 扩展：心态/避坑 置前（信息差高频维度），旧分类兼容保留
CATEGORY_RULES = [
    ("避坑", ["避坑", "踩坑", "教训", "劝退", "避雷", "不建议", "别做"]),
    ("心态", ["心态", "焦虑", "压力", "崩溃", "坚持", "想放弃", "emo"]),
    ("复试", ["复试"]),
    ("调剂", ["调剂"]),
    ("择校", ["择校", "选校"]),
    ("备考", ["备考", "初试"]),
    ("复习", ["复习"]),
]

# 考研资讯专用分类（信息差维度，按优先级排序——命中前面的关键词优先归类）。
# 与 CATEGORY_RULES（经验贴）分离：资讯维度更细，且"复试分数线"应归"复试线"而非"复试"。
KAOYAN_CATEGORY_RULES = [
    ("调剂", ["调剂", "调剂系统", "调剂名额", "调剂信息"]),
    ("复试线", ["复试线", "国家线", "自划线", "分数线", "院线", "校线"]),
    ("复试", ["复试", "面试", "复试名单", "拟录取"]),
    (
        "招生简章",
        ["招生简章", "招生章程", "招生计划", "招生目录", "专业目录", "硕士招生", "博士招生"],
    ),
    ("推免", ["推免", "保研", "推荐免试", "免试攻读"]),
    ("报录比", ["报录比", "录取比例", "报考人数", "报名人数", "录取人数"]),
    (
        "政策",
        [
            "政策",
            "报名",
            "初试",
            "考试时间",
            "考试大纲",
            "网报",
            "网上确认",
            "报考",
            "教育部",
            "通知",
        ],
    ),
    ("择校", ["择校", "选校", "院校选择"]),
    ("备考", ["备考", "复习", "真题", "资料", "经验"]),
]

# 用于判断 RSS 非中文条目是否与考研相关
KAOYAN_MARKERS = [
    "考研",
    "硕士",
    "研究生",
    "graduate",
    "master",
    "phd",
    "kaoyan",
]

# ----------------------------------------------------------------------
# 平台领域词表（主题相关度门禁，S1）
# ----------------------------------------------------------------------
# 平台覆盖领域：考研 / 考公 / 考证执业 / 就业求职 / 在校学业。
# 命中任一即为"平台领域内容"（不限于考研——用户背景含考公/考证/就业，见身份覆盖纪律）。
# 经验贴/资讯/爬取内容在爬取→评分→聚合三层都做该判定，杜绝游戏/娱乐等无关内容混入。
PLATFORM_DOMAIN_KEYWORDS = [
    # 考研
    "考研", "备考", "复试", "调剂", "初试", "择校", "选校", "上岸", "二战", "三战",
    "研究生", "硕士", "博士", "导师", "推免", "保研", "拟录取", "录取", "报录比",
    "408", "数据结构", "计算机组成原理", "操作系统", "计算机网络", "高等数学", "线性代数",
    "肖秀荣", "政治", "英语一", "英语二", "专业课", "真题", "模拟卷",
    # 考公（公考/省考/国考/事业单位/编制）
    "考公", "公务员", "国考", "省考", "联考", "行测", "申论", "事业单位", "事业编制",
    "上岸公务员", "选调生", "编制", "体制内", "面试", "政审", "体检", "职位表", "岗位报考",
    "粉笔", "华图", "中公", "公考雷达",
    # 考证执业
    "考证", "执业资格", "教师资格证", "教资", "法考", "注会", "CPA", "注册会计",
    "注册会计师", "一级建造师", "二建", "会计初级", "经济师", "社工证", "人力资管",
    "软考", "计算机等级", "四六级", "英语六级", "雅思", "托福",
    # 就业求职
    "就业", "求职", "简历", "面试", "offer", "校招", "春招", "秋招", "网申", "实习",
    "职业规划", "职业发展", "跳槽", "薪资", "薪酬", "转行", "职业技能", "副业",
    # 在校学业
    "大学", "专业", "选专业", "转专业", "绩点", "保研", "毕业论文", "毕业设计", "考研数学",
    "专升本", "高考", "志愿填报", "大学生", "学生会",
    # 职业/考试通用
    "经验", "攻略", "方法", "技巧", "计划", "时间表", "笔记",
]

# 明确离题黑名单（游戏 / 娱乐 / 与职业提升无关）。命中任一即打断：
# 即便标题含"心态/压力/坚持"等通用词（如三角洲游戏教学"保持心态"），
# 只要命中强离题词即判为离题，不进入平台内容流。
OFF_TOPIC_REJECT_KEYWORDS = [
    # 游戏
    "三角洲", "三角洲行动", "原神", "王者荣耀", "和平精英", "英雄联盟", "LOL",
    "绝地求生", "PUBG", "CSGO", "CS2", "无畏契约", "瓦罗兰特", "FPS", "射击游戏",
    "游戏攻略", "游戏教学", "外挂", "开黑", "排位", "上分", "匹配", "对局", "段位",
    "原神抽卡", "崩坏", "星穹铁道", "明日方舟", "阴阳师", "元气骑士", "我的世界",
    "switch", "ps5", "steam", "单机游戏", "手游", "端游", "电竞", "主播",
    # 娱乐 / 非职业提升
    "明星", "娱乐圈", "绯闻", "综艺", "选秀", "八卦", "吃瓜", "追剧", "电视剧",
    "电影解说", "音乐现场", "演唱会", "篮球", "足球", "体育赛事", "NBA", "世界杯",
    "美食", "探店", "旅游攻略", "穿搭", "美妆", "护肤", "明星同款",
    "冷笑话", "搞笑视频", "沙雕", "段子", "宠物", "猫", "狗", "萌宠",
    "恋爱", "婚姻", "八卦感情", "星座", "塔罗", "占卜",
]

# 领域判定返回的 domain 标签
_DOMAIN_LABELS = ("kaoyan", "gongkao", "certificate", "employment", "study")


def _infer_domain(title: str, content: str) -> str | None:
    """按领域词命中推断内容归属领域（标题+正文拼接后精确匹配）。

    与 classify_topic_relevance 的第二步互补：判定"相关"后给出归属标签。
    用独立映射避免 substring 误判（如"面试"通用词在就业/考公都出现时不误归）。
    """
    text = f"{title or ''} {content or ''}".lower()
    _mapping = [
        ("kaoyan", ["考研", "复试", "调剂", "初试", "择校", "选校", "上岸", "二战", "三战",
                    "研究生", "硕士", "博士", "导师", "推免", "保研", "拟录取", "录取", "报录比",
                    "408", "数据结构", "计算机组成原理", "操作系统", "计算机网络", "高等数学", "线性代数",
                    "肖秀荣", "政治", "英语一", "英语二", "专业课", "真题", "模拟卷", "考研数学"]),
        ("gongkao", ["考公", "公务员", "国考", "省考", "联考", "行测", "申论", "事业单位", "事业编制",
                     "上岸公务员", "选调生", "编制", "体制内", "政审", "体检", "职位表", "岗位报考",
                     "粉笔", "华图", "中公", "公考雷达"]),
        ("certificate", ["考证", "执业资格", "教师资格证", "教资", "法考", "注会", "CPA", "注册会计",
                         "注册会计师", "一级建造师", "二建", "会计初级", "经济师", "社工证", "人力资管",
                         "软考", "计算机等级", "四六级", "英语六级", "雅思", "托福"]),
        ("employment", ["就业", "求职", "简历", "offer", "校招", "春招", "秋招", "网申", "实习",
                        "职业规划", "职业发展", "跳槽", "薪资", "薪酬", "转行", "职业技能", "副业"]),
        ("study", ["大学", "专业", "选专业", "转专业", "绩点", "毕业论文", "毕业设计", "专升本",
                   "高考", "志愿填报", "大学生", "学生会"]),
    ]
    for domain, kws in _mapping:
        if any(kw.lower() in text for kw in kws):
            return domain
    # 通用词（面试/经验等）不作为归属判据，返回 None
    return None


def classify_topic_relevance(
    title: str,
    content: str = "",
    tags: list[str] | None = None,
) -> tuple[bool, str, str | None]:
    """主题相关度判定（第一性原理：领域相关是内容进入平台流的前提）。

    Returns:
        (is_off_topic, reason, domain)
        - is_off_topic True：应拦截（命中离题黑名单，或完全无领域词）
        - reason：判定说明（命中黑名单词 / 无领域词）
        - domain：命中的领域标签（kaoyan/gongkao/certificate/employment/study），未命中 None

    判定策略（避免伪度量：不只看名校/长度，看语义相关）：
        1) 命中 OFF_TOPIC_REJECT_KEYWORDS → 立即判离题（即使含"心态/压力"等通用词）
        2) 命中 PLATFORM_DOMAIN_KEYWORDS → 相关（返回归属领域）
        3) 均未命中 → 离题（无领域信号，不进平台流）
    """
    title_s = str(title or "")
    content_s = str(content or "")
    tags_s = " ".join(str(t) for t in (tags or []) if t is not None)
    text = " ".join(filter(None, [title_s, content_s, tags_s])).lower()

    if not text:
        return True, "无文本可判定", None

    # 1) 离题黑名单：命中即离题（强信号，优先级最高）。
    #    通用情绪词（心态/压力/坚持）不在此列——它们是否离题取决于是否命中黑名单。
    for kw in OFF_TOPIC_REJECT_KEYWORDS:
        if kw.lower() in text:
            return True, f"命中离题词「{kw}」", None

    # 2) 领域词：判定相关并标注归属领域。用标题优先、正文兜底，
    #    命中任一领域词即相关。
    for kw in PLATFORM_DOMAIN_KEYWORDS:
        if kw.lower() in text:
            domain = _infer_domain(title_s, content_s)
            return False, "", domain

    # 3) 完全无领域信号 → 离题
    return True, "未命中任何领域信号", None


class ResearchTransformer:
    """将外部调研 crawler 输出清洗、去重并结构化。"""

    @staticmethod
    def _strip_html(value: Any) -> str:
        """去除 HTML 标签并解码 HTML 实体。"""
        text = str(value) if value is not None else ""
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        return text

    @staticmethod
    def _clean_text(value: Any) -> str:
        """清理文本：去除首尾空白、统一换行。"""
        text = str(value) if value is not None else ""
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        return text

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _extract_tags(cls, text: str) -> list[str]:
        """从文本中提取学科与阶段标签。"""
        text = text.lower()
        tags: list[str] = []
        for kw in SUBJECT_KEYWORDS + STAGE_KEYWORDS:
            if kw.lower() in text and kw not in tags:
                tags.append(kw)
        return tags

    @classmethod
    def _infer_category(cls, title: str) -> str:
        """根据标题关键词推断经验贴分类。"""
        title_lower = title.lower()
        for category, keywords in CATEGORY_RULES:
            if any(kw.lower() in title_lower for kw in keywords):
                return category
        return "general"

    @classmethod
    def _infer_news_category(cls, title: str) -> str:
        """按标题关键词推断考研资讯分类（信息差维度，优先级排序）。"""
        title_lower = title.lower()
        for category, keywords in KAOYAN_CATEGORY_RULES:
            if any(kw.lower() in title_lower for kw in keywords):
                return category
        return "general"

    @classmethod
    def _contains_ad(cls, text: str) -> bool:
        """判断是否包含广告/引流关键词。"""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in AD_KEYWORDS)

    @classmethod
    def _is_kaoyan_related(cls, title: str) -> bool:
        """判断标题是否与考研相关（用于过滤 RSS 纯英文无关条目）。"""
        if any(kw.lower() in title.lower() for kw in KAOYAN_MARKERS):
            return True
        # 包含中文字符则认为与中文语境相关
        if re.search(r"[\u4e00-\u9fff]", title):
            return True
        return False

    @classmethod
    def _is_quality_ok(cls, title: str, content: str, platform: str) -> bool:
        """质量过滤：标题过短、含广告、纯英文且与考研无关的均丢弃。"""
        if len(title.strip()) < 5:
            return False
        if cls._contains_ad(title + "\n" + content):
            return False
        if platform == "rss" and not cls._is_kaoyan_related(title):
            return False
        return True

    @classmethod
    def _dedup_by_url(cls, items: list[dict]) -> list[dict]:
        """基于 source_url 去重，保留第一条。无 source_url 的条目会被丢弃。"""
        seen: set[str] = set()
        result: list[dict] = []
        for item in items:
            url = item.get("source_url")
            if not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            result.append(item)
        return result

    @classmethod
    def transform_bilibili(cls, items: list[dict], source_platform: str = "bilibili") -> list[dict]:
        """将 B站/知乎/贴吧经验内容转换为 ExperiencePost payload。

        source_platform 可选参（默认 "bilibili" 保兼容）：
        知乎专栏（zhihu）/ 贴吧避坑帖（tieba）复用同一清洗/去重逻辑。
        """
        payloads: list[dict] = []
        for raw in items:
            title = cls._clean_text(cls._strip_html(raw.get("title", "")))
            author = cls._clean_text(raw.get("author", ""))
            bvid = cls._clean_text(raw.get("bvid", ""))
            source_url = cls._clean_text(raw.get("source_url", ""))
            if not source_url and bvid:
                source_url = f"https://www.bilibili.com/video/{bvid}"

            view_count = cls._to_int(raw.get("view_count"))
            like_count = cls._to_int(raw.get("like_count"))

            raw_summary = cls._clean_text(raw.get("summary") or raw.get("content") or title)
            raw_content = cls._clean_text(raw.get("content") or raw.get("summary") or title)

            if not cls._is_quality_ok(title, raw_content, source_platform):
                continue

            # 主题相关度门禁（S1）：命中离题黑名单直接丢弃（如三角洲/王者荣耀等
            # 游戏视频，即使标题含"心态/压力"通用词也判离题）。无领域词信号的内容
            # 留待 promote 层打标，避免冷启动供给侧过度裁剪。
            is_off_topic, off_reason, _domain = classify_topic_relevance(
                title, raw_content, raw.get("tags")
            )
            if is_off_topic and off_reason.startswith("命中离题词"):
                logger.info("[transform] 主题离题丢弃: %s（%s）", title[:40], off_reason)
                continue

            summary = raw_summary[:500]
            existing_tags = [t for t in raw.get("tags", []) if isinstance(t, str)]
            extracted_tags = cls._extract_tags(f"{title} {raw_content}")
            tags = list(dict.fromkeys(existing_tags + extracted_tags))
            category = cls._infer_category(title)

            content_lines = [
                f"作者：{author or '未知'}",
                f"播放量：{view_count}",
                f"标签：{', '.join(tags)}",
                "",
                raw_content,
            ]
            content = "\n".join(content_lines)

            payloads.append(
                {
                    "user_id": SYSTEM_USER_ID,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "tags": tags,
                    "category": category,
                    "source_platform": source_platform,
                    "source_url": source_url,
                    "external_view_count": view_count,
                    "external_like_count": like_count,
                    "status": "pending",
                    "is_verified": False,
                    "is_anonymous": False,
                }
            )

        return cls._dedup_by_url(payloads)

    @classmethod
    def transform_web(cls, items: list[dict]) -> list[dict]:
        """将网页文章转换为 ExperiencePost payload。"""
        payloads: list[dict] = []
        for raw in items:
            raw_title = cls._clean_text(raw.get("title", ""))
            # Jina Reader 可能带有 "Title: " 前缀
            if raw_title.lower().startswith("title:"):
                raw_title = raw_title[6:].strip()
            title = cls._clean_text(cls._strip_html(raw_title))
            content = cls._clean_text(raw.get("content", ""))
            source_url = cls._clean_text(raw.get("source_url", ""))

            # 过滤掉反爬/登录拦截页面
            if any(
                marker in content
                for marker in [
                    "安全验证",
                    "CAPTCHA",
                    "please make sure you are authorized",
                    "请您登录后查看",
                ]
            ):
                continue

            if not cls._is_quality_ok(title, content, "web"):
                continue

            # 主题相关度门禁（S1）：命中离题黑名单直接丢弃。
            is_off_topic, off_reason, _domain = classify_topic_relevance(title, content)
            if is_off_topic and off_reason.startswith("命中离题词"):
                logger.info("[transform] 主题离题丢弃: %s（%s）", title[:40], off_reason)
                continue

            summary = content[:500]
            tags = cls._extract_tags(f"{title} {content}")
            category = cls._infer_category(title)

            payloads.append(
                {
                    "user_id": SYSTEM_USER_ID,
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "tags": tags,
                    "category": category,
                    "source_platform": "web",
                    "source_url": source_url,
                    "external_view_count": 0,
                    "external_like_count": 0,
                    "status": "pending",
                    "is_verified": False,
                    "is_anonymous": False,
                }
            )

        return cls._dedup_by_url(payloads)

    @classmethod
    def transform_rss(cls, items: list[dict]) -> list[dict]:
        """将 RSS 资讯转换为 KaoyanNews payload。"""
        payloads: list[dict] = []
        for raw in items:
            title = cls._clean_text(cls._strip_html(raw.get("title", "")))
            summary = cls._clean_text(raw.get("summary", ""))[:500]
            content = cls._clean_text(raw.get("content", ""))
            source_url = cls._clean_text(raw.get("source_url", ""))

            if not cls._is_quality_ok(title, content or summary, "rss"):
                continue

            # 主题相关度门禁（S1）：命中离题黑名单直接丢弃。
            is_off_topic, off_reason, _domain = classify_topic_relevance(title, content or summary)
            if is_off_topic and off_reason.startswith("命中离题词"):
                logger.info("[transform] 主题离题丢弃: %s（%s）", title[:40], off_reason)
                continue

            existing_tags = [t for t in raw.get("tags", []) if isinstance(t, str)]
            extracted_tags = cls._extract_tags(f"{title} {summary} {content}")
            tags = list(dict.fromkeys(existing_tags + extracted_tags))

            # 分类：信息差维度规则优先；规则未命中时沿用采集器自带栏目（若为已知维度）
            category = cls._infer_news_category(title)
            if category == "general":
                raw_category = raw.get("category", "")
                if isinstance(raw_category, str) and raw_category in dict(KAOYAN_CATEGORY_RULES):
                    category = raw_category

            published_at = raw.get("published_at")
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at)
                except ValueError:
                    published_at = None
            elif not isinstance(published_at, datetime):
                published_at = None

            crawled_at = raw.get("crawled_at")
            if isinstance(crawled_at, str):
                try:
                    crawled_at = datetime.fromisoformat(crawled_at)
                except ValueError:
                    crawled_at = None
            if not isinstance(crawled_at, datetime):
                crawled_at = datetime.now(timezone.utc)

            quality_score, quality_grade = score_item(
                title=title,
                content=content,
                summary=summary,
                source_url=source_url,
                published_at=published_at,
                crawled_at=crawled_at,
            )

            payloads.append(
                {
                    "title": title,
                    "summary": summary or None,
                    "content": content or None,
                    "source_platform": raw.get("source_platform", "rss") or "rss",
                    "source_url": source_url,
                    "published_at": published_at,
                    "crawled_at": crawled_at,
                    "status": "pending",
                    "category": category,
                    "tags": tags,
                    "quality_score": quality_score,
                    "quality_grade": quality_grade,
                }
            )

        return cls._dedup_by_url(payloads)
