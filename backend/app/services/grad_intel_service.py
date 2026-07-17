"""考研情报服务层 — 院校情报 AI 查询、自我定位 AI 评估、暗知识预填充。

考研本质是信息战。这三个服务分别解决：
1. 院校隐性信息不透明 → AI 基于公开信息生成结构化院校情报
2. 自我定位模糊 → AI 基于背景数据生成三档院校推荐
3. "你不知道你不知道" → 预填充的真实盲区知识
"""
import hashlib
import json
import logging
import re
import time
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.grad_intel import (
    DarkKnowledge,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
    SelfPositioning,
)
from app.services.ai_service import AIService, AIServiceNotConfigured

logger = logging.getLogger(__name__)

# ======================================================================
# AI 结果缓存 — 基于输入哈希，24小时 TTL
# 优化：使用 RedisCache（自动降级内存缓存），支持多 worker 共享
# 原进程内 _ai_cache dict 在多 worker 时命中率极低（~1/N）
# ======================================================================
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CACHE_PREFIX = "ai_positioning"


def _compute_cache_key(data: dict) -> str:
    """计算输入数据的哈希作为缓存键。"""
    key_fields = {
        "undergrad_tier": data.get("undergrad_tier", ""),
        "undergrad_major": data.get("undergrad_major", ""),
        "gpa": data.get("gpa"),
        "gpa_rank": data.get("gpa_rank", ""),
        "english_level": data.get("english_level", ""),
        "english_score": data.get("english_score"),
        "target_major": data.get("target_major", ""),
        "target_region": data.get("target_region", ""),
        "target_school": data.get("target_school", ""),
    }
    key_str = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_cached_result(cache_key: str) -> dict | None:
    """获取缓存的 AI 结果（Redis 优先，自动降级内存缓存）。"""
    full_key = f"{CACHE_PREFIX}:{cache_key}"
    result = cache.get(full_key)
    if result is not None:
        logger.info("AI 结果缓存命中: %s", cache_key[:8])
    return result


def _set_cached_result(cache_key: str, result: dict) -> None:
    """缓存 AI 结果到 Redis。"""
    full_key = f"{CACHE_PREFIX}:{cache_key}"
    cache.set(full_key, result, ttl=CACHE_TTL_SECONDS)
    logger.info("AI 结果已缓存: %s", cache_key[:8])


# ======================================================================
# 静态降级推荐 — LLM 不可用时的兜底方案
# ======================================================================
def _get_static_recommendations(data: dict) -> dict:
    """基于规则生成静态推荐（LLM 不可用时的降级方案）。"""
    undergrad_tier = data.get("undergrad_tier", "")
    gpa = data.get("gpa") or 0
    target_major = data.get("target_major", "")
    target_region = data.get("target_region", "")

    # 根据本科层次和 GPA 确定推荐档次
    if undergrad_tier in ["985", "211"] and gpa >= 3.5:
        reach_schools = [
            {"name": "清华大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 35, "reason": "顶尖院校，竞争激烈"},
            {"name": "北京大学", "major": target_major or "软件工程", "tier": "985", "probability": 30, "reason": "学术氛围浓厚"},
        ]
        target_schools = [
            {"name": "浙江大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 65, "reason": "工科强校，录取相对公平"},
            {"name": "上海交通大学", "major": target_major or "电子信息", "tier": "985", "probability": 60, "reason": "地理位置优越"},
            {"name": "中国科学技术大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 55, "reason": "科研实力强"},
        ]
        safety_schools = [
            {"name": "南京大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 85, "reason": "保底选择，录取概率高"},
            {"name": "华中科技大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 80, "reason": "工科强校，相对稳妥"},
        ]
        success_probability = 55
    elif undergrad_tier in ["985", "211", "双一流"] and gpa >= 3.0:
        reach_schools = [
            {"name": "浙江大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 40, "reason": "冲刺选择"},
            {"name": "上海交通大学", "major": target_major or "电子信息", "tier": "985", "probability": 35, "reason": "竞争激烈"},
        ]
        target_schools = [
            {"name": "南京大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 65, "reason": "匹配当前水平"},
            {"name": "武汉大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 60, "reason": "综合性大学"},
            {"name": "中山大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 55, "reason": "华南地区强校"},
        ]
        safety_schools = [
            {"name": "四川大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 85, "reason": "保底选择"},
            {"name": "吉林大学", "major": target_major or "计算机科学与技术", "tier": "985", "probability": 80, "reason": "录取概率高"},
        ]
        success_probability = 50
    elif undergrad_tier in ["一本", "二本"] and gpa >= 3.0:
        reach_schools = [
            {"name": "南京航空航天大学", "major": target_major or "计算机科学与技术", "tier": "211", "probability": 40, "reason": "冲刺选择"},
            {"name": "北京交通大学", "major": target_major or "计算机科学与技术", "tier": "211", "probability": 35, "reason": "地理位置好"},
        ]
        target_schools = [
            {"name": "杭州电子科技大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 65, "reason": "IT 就业好"},
            {"name": "南京邮电大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 60, "reason": "通信强校"},
            {"name": "重庆邮电大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 55, "reason": "西南地区强校"},
        ]
        safety_schools = [
            {"name": "浙江工业大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 85, "reason": "保底选择"},
            {"name": "广东工业大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 80, "reason": "珠三角就业好"},
        ]
        success_probability = 45
    else:
        reach_schools = [
            {"name": "杭州电子科技大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 35, "reason": "冲刺选择"},
        ]
        target_schools = [
            {"name": "浙江工业大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 60, "reason": "匹配当前水平"},
            {"name": "南京邮电大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 55, "reason": "专业实力强"},
        ]
        safety_schools = [
            {"name": "浙江理工大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 85, "reason": "保底选择"},
            {"name": "江苏大学", "major": target_major or "计算机科学与技术", "tier": "一本", "probability": 80, "reason": "录取概率高"},
        ]
        success_probability = 35

    return {
        "ai_assessment": None,  # 标记为降级模式
        "reach_schools": reach_schools,
        "target_schools": target_schools,
        "safety_schools": safety_schools,
        "success_probability": success_probability,
        "risk_warnings": [
            "当前为静态推荐模式，AI 服务暂时不可用",
            "建议稍后重新生成以获取个性化分析",
            "以上推荐基于规则引擎，仅供参考",
        ],
    }


# ======================================================================
# 暗知识预填充数据 — 考研全流程中"你不知道你不知道"的盲区知识
# 基于过来人经验、考研论坛、知乎等公开信息整理
# ======================================================================
DARK_KNOWLEDGE_SEED = [
    # ===== 阶段1: 决策阶段 =====
    {
        "stage": "decision",
        "category": "ROI评估",
        "title": "考研报名人数已连降两年，但好学校竞争更激烈了",
        "content": "2025年考研报名人数从438万降至402万，但985/211院校的竞争并未缓解。原因是推免比例持续扩大，实际统考名额在减少。人数下降主要发生在普通院校，名校反而更卷了。",
        "importance": "high",
        "common_misconception": "很多人以为报名人数少了就好考了，实际上名校的竞争反而更激烈了，因为推免占了更多名额。",
        "actionable_advice": "择校时不要看总报名人数，要看目标院校目标专业的实际统考名额（总名额减推免名额）。",
        "verification_method": "在目标院校研究生院官网查招生目录，对比推免录取名单和统考录取名单，算出真实统考名额。",
        "tags": ["报名人数", "推免", "竞争"],
        "sort_order": 1,
    },
    {
        "stage": "decision",
        "category": "方向选择",
        "title": "专硕vs学硕的区别比你想的大",
        "content": "专硕和学硕不只是「学制不同」。专硕通常学费更高（部分名校金融专硕学费10万+），培养偏应用，但考博时可能受限；学硕学费低，培养偏学术，考博更顺畅。部分院校专硕不提供住宿。",
        "importance": "high",
        "common_misconception": "很多人以为专硕就是「容易版的学硕」，实际上两者培养方向完全不同，就业方向也有差异。",
        "actionable_advice": "明确自己考研目的：就业导向选专硕，学术/考博导向选学硕。同时对比学费、住宿、奖助学金差异。",
        "verification_method": "查看目标院校招生简章中「专业学位」和「学术学位」的培养方案对比。",
        "tags": ["专硕", "学硕", "学费", "培养方向"],
        "sort_order": 2,
    },
    {
        "stage": "decision",
        "category": "方向选择",
        "title": "跨考的隐性成本远超你的想象",
        "content": "跨考不只是「专业课从零开始」。隐性成本包括：1) 信息差更大——找不到直系学长学姐和真题；2) 复试可能被问「为什么跨考」且答案影响评分；3) 部分院校对跨考生有加试要求；4) 导师可能更倾向本专业学生。",
        "importance": "high",
        "common_misconception": "很多人以为跨考只要初试分数高就行，实际上复试时跨考身份可能成为劣势。",
        "actionable_advice": "跨考前务必确认目标院校是否接受跨考生（看招生简章备注），并提前联系导师确认态度。",
        "verification_method": "查看招生简章「报考条件」部分，搜索目标院校+跨考的经验贴。",
        "tags": ["跨考", "隐性成本", "复试"],
        "sort_order": 3,
    },
    {
        "stage": "decision",
        "category": "政策风险",
        "title": "同等学力考研有额外门槛",
        "content": "专科毕业两年可以同等学力身份考研，但多数985/211院校对同等学力有加试要求（通常加试2门本科主干课程），部分院校甚至不招收同等学力考生。且同等学力考生不能跨专业报考。",
        "importance": "critical",
        "common_misconception": "很多人以为专科毕业两年就能和本科生一样考研，实际上有很多隐性限制。",
        "actionable_advice": "同等学力考生务必提前确认目标院校是否招收，以及加试科目和要求。",
        "verification_method": "查看招生简章「报考条件」中关于同等学力的具体要求。",
        "tags": ["同等学力", "专科考研", "加试"],
        "sort_order": 4,
    },

    # ===== 阶段2: 择校阶段 =====
    {
        "stage": "school_selection",
        "category": "隐性门槛",
        "title": "卡第一学历是真实存在的",
        "content": "部分985/211院校在复试时会参考考生本科出身。虽然初试分数是硬门槛，但在复试面试中，本科背景可能影响评分。典型表现：同等分数下优先录取985/211本科生，双非考生需要明显更高的分数才能上岸。",
        "importance": "critical",
        "common_misconception": "很多人以为初试分数高就不看本科，实际上复试时本科背景是隐性参考因素。",
        "actionable_advice": "双非考生择校时优先选择「保护第一志愿、复试公平」的院校。在知乎、考研论坛搜索「XX大学 卡学历」看过来人反馈。",
        "verification_method": "搜索目标院校的复试名单和录取名单，对比录取学生的本科背景分布。如果录取名单中双非占比极低，说明可能存在卡学历。",
        "tags": ["卡学历", "第一学历", "复试", "双非"],
        "sort_order": 5,
    },
    {
        "stage": "school_selection",
        "category": "录取公平性",
        "title": "保护第一志愿 vs 压分收调剂",
        "content": "部分院校会故意压低第一志愿考生的专业课分数，使一志愿过线人数减少，从而腾出名额接收优质调剂生（如985落榜生）。相反，「保护一志愿」的院校会将一志愿和调剂生分开排序，优先录取一志愿。",
        "importance": "critical",
        "common_misconception": "很多人以为所有院校都公平对待一志愿，实际上压分收调剂是行业内公开的秘密。",
        "actionable_advice": "择校时务必搜索「XX大学 压分」和「XX大学 保护一志愿」。保护一志愿的院校通常在复试办法中明确写「一志愿优先」。",
        "verification_method": "查看目标院校研究生院官网的复试办法，看是否明确「一志愿与调剂生分开排序」。对比历年一志愿录取率和调剂录取率。",
        "tags": ["保护一志愿", "压分", "调剂", "公平性"],
        "sort_order": 6,
    },
    {
        "stage": "school_selection",
        "category": "数据陷阱",
        "title": "报录比会骗人——推免占比是关键变量",
        "content": "招生简章上的「拟招生人数」包含推免生。某985金融专硕报录比看似15:1，但推免占了60%，实际统考报录比可能高达40:1。很多考生直到报名结束都不知道这个关键信息。",
        "importance": "critical",
        "common_misconception": "很多人只看报录比，不查推免比例，严重低估了实际竞争烈度。",
        "actionable_advice": "择校时必须计算「真实统考名额 = 拟招生人数 - 推免录取人数」。在研招网和院校官网查推免录取名单。",
        "verification_method": "目标院校研究生院官网通常会公示推免拟录取名单。用拟招生总人数减去推免录取人数，得到真实统考名额。",
        "tags": ["报录比", "推免", "统考名额", "数据陷阱"],
        "sort_order": 7,
    },
    {
        "stage": "school_selection",
        "category": "导师选择",
        "title": "导师选择比学校选择更重要",
        "content": "好学校的差导师 vs 差学校的好导师——前者可能让你痛不欲生3年，后者可能让你脱胎换骨。导师的学术水平、人品、管理风格直接决定你的研究生体验。延期毕业、心理问题往往和导师有关。",
        "importance": "high",
        "common_misconception": "很多人只看学校排名，完全忽略导师因素，入学后才发现导师不合适。",
        "actionable_advice": "择校阶段就开始了解目标院校的导师信息。查导师的论文发表、课题项目、学生评价。在导师评价网、知乎搜索导师姓名。",
        "verification_method": "在中国知网查导师近年论文发表情况；在导师评价类网站看学生评价；联系导师的在读研究生了解真实情况。",
        "tags": ["导师", "选择", "研究生体验"],
        "sort_order": 8,
    },
    {
        "stage": "school_selection",
        "category": "专业课信息",
        "title": "专业课自命题 vs 统考——信息透明度天差地别",
        "content": "统考专业课（如计算机408）有标准大纲和公开真题，信息透明。自命题专业课由院校自主出题，大纲可能模糊，真题可能不公开，信息差极大。部分院校9月突然更改考试科目，导致考生半年复习白费。",
        "importance": "high",
        "common_misconception": "很多人以为所有专业课都有标准复习资料，实际上自命题院校的信息获取难度远超想象。",
        "actionable_advice": "如果选自命题院校，必须找到直系上岸学长学姐获取真题和重点。9月密切关注官网大纲变动。",
        "verification_method": "查看目标院校研究生院官网的招生目录和考试大纲。搜索「XX大学 XX专业 真题」看是否有公开渠道。",
        "tags": ["自命题", "统考", "真题", "信息差"],
        "sort_order": 9,
    },

    # ===== 阶段3: 备考阶段 =====
    {
        "stage": "preparation",
        "category": "复习策略",
        "title": "专业课占60%总分，是拉分关键",
        "content": "考研总分500分，专业课占300分（60%）。公共课（政治100+英语100）拉不开太大差距，真正决定成败的是专业课和数学。很多考生在公共课上花太多时间，专业课反而投入不足。",
        "importance": "high",
        "common_misconception": "很多人认为政治英语也要花大量时间，实际上专业课和数学才是拉分核心。",
        "actionable_advice": "时间分配上专业课≥40%，数学≥30%（如考数学），英语15%，政治15%。9月后政治比例可提高。",
        "verification_method": "统计自己各科目投入时间占比，与建议比例对比调整。",
        "tags": ["专业课", "时间分配", "拉分"],
        "sort_order": 10,
    },
    {
        "stage": "preparation",
        "category": "复习策略",
        "title": "暑假是分水岭——7-8月复习质量决定成败",
        "content": "暑假是唯一可以全身心投入复习的时段。统计数据表明，暑假坚持每天8小时以上有效学习的考生，上岸率显著高于暑假松懈的考生。暑假后开始冲刺已经来不及了。",
        "importance": "high",
        "common_misconception": "很多人以为9月开学后再认真也来得及，实际上暑假是建立基础的关键期。",
        "actionable_advice": "暑假前制定详细的每日复习计划。7-8月保持每天8-10小时有效学习，重点攻克专业课和数学。",
        "verification_method": "每周自测各科目掌握程度，对比月初和月末的进步情况。",
        "tags": ["暑假", "分水岭", "复习质量"],
        "sort_order": 11,
    },
    {
        "stage": "preparation",
        "category": "信息搜集",
        "title": "英语真题是最重要的资料——模拟题质量远不如真题",
        "content": "考研英语真题的出题思路和难度是高度一致的，而市面上的模拟题质量参差不齐。近10年真题至少刷3遍，每篇阅读都要精读到能翻译全文。模拟题最多作为练手，不能替代真题。",
        "importance": "medium",
        "common_misconception": "很多人以为多刷模拟题就能提高，实际上真题的出题逻辑是模拟题无法复制的。",
        "actionable_advice": "英语复习以近10-15年真题为核心。每套真题刷3遍：第1遍做题，第2遍精读翻译，第3遍分析出题逻辑。",
        "verification_method": "测试自己能否准确翻译真题阅读全文，能否说出每道题的出题意图。",
        "tags": ["英语", "真题", "复习资料"],
        "sort_order": 12,
    },
    {
        "stage": "preparation",
        "category": "信息搜集",
        "title": "不要迷信经验贴——别人的成功不可复制",
        "content": "经验贴往往存在幸存者偏差——只有成功上岸的人才会发帖。而且发帖者可能隐去了关键前提（如本科基础好、有内部资源）。盲目照搬别人的复习计划和方法，可能适得其反。",
        "importance": "medium",
        "common_misconception": "很多人把经验贴当圣经照搬，忽视了自己的基础和目标院校的差异。",
        "actionable_advice": "经验贴只作参考，提取共性（如「暑假很重要」），不照搬个性（如「三个月上岸985」）。根据自己的基础和目标制定计划。",
        "verification_method": "对比3-5篇目标院校同专业的经验贴，提取共同点作为参考，差异点根据自身情况判断。",
        "tags": ["经验贴", "幸存者偏差", "复习计划"],
        "sort_order": 13,
    },

    # ===== 阶段4: 初试后 =====
    {
        "stage": "exam",
        "category": "复试准备",
        "title": "复试准备要趁早——不要等分数线出来再开始",
        "content": "初试结束后就应该开始准备复试，而不是等2月分数线公布。很多院校复试包含笔试、面试、英语口语等多个环节，需要1-2个月准备。等分数线出来再准备，往往来不及。",
        "importance": "high",
        "common_misconception": "很多人以为初试考完可以放松，等分数线出来再准备复试，实际上时间根本不够。",
        "actionable_advice": "初试结束休息1周后就开始复试准备。联系导师、准备专业课笔试、练习英语口语、准备自我介绍。",
        "verification_method": "查看目标院校去年复试时间和流程，倒推需要多少准备时间。",
        "tags": ["复试", "时间规划", "准备"],
        "sort_order": 14,
    },
    {
        "stage": "exam",
        "category": "导师联系",
        "title": "联系导师的正确时机和方式",
        "content": "初试成绩出来后（2月下旬）是联系导师的最佳时机。太早联系导师没空理你，太晚联系好导师已经被抢。邮件要简洁专业：自我介绍+初试成绩+研究兴趣+附件简历。不要同时群发多个导师。",
        "importance": "high",
        "common_misconception": "很多人以为初试前就要联系导师，或者同时群发多个导师，实际上时机和方式都很重要。",
        "actionable_advice": "2月下旬出分后，给1-2位意向导师发邮件。邮件正文200字以内，附PDF简历。48小时没回可发第二位。",
        "verification_method": "查看导师近年论文了解研究方向，确保邮件中提到的兴趣和导师方向匹配。",
        "tags": ["联系导师", "邮件", "时机"],
        "sort_order": 15,
    },
    {
        "stage": "exam",
        "category": "调剂",
        "title": "调剂是信息战不是分数战——好名额几小时内被抢光",
        "content": "调剂系统开放后，好学校的调剂名额往往在几小时内就被抢光。提前不搜集信息的考生，等系统开放再找学校已经来不及了。很多院校在正式调剂系统开放前就有「预调剂」 informal 通道。",
        "importance": "critical",
        "common_misconception": "很多人以为调剂就是等系统开放后填报，实际上提前不准备根本抢不到好名额。",
        "actionable_advice": "初试成绩出来后如果觉得不稳，立刻开始搜集可能有调剂名额的院校。提前联系院校研招办和导师。",
        "verification_method": "关注目标院校研招办官网和公众号，搜索往年调剂信息。在研招网调剂系统开放前就准备好备选院校清单。",
        "tags": ["调剂", "信息战", "预调剂"],
        "sort_order": 16,
    },

    # ===== 阶段5: 复试阶段 =====
    {
        "stage": "retest",
        "category": "复试策略",
        "title": "复试占比高 = 逆袭机会大",
        "content": "复试占比50%以上的学校，初试分数差距可以被大幅缩小。初试排名靠后的考生完全有机会通过复试逆袭。相反，复试占比30%以下的学校，初试分数基本决定结果。",
        "importance": "high",
        "common_misconception": "很多人以为初试分数低就没希望了，实际上复试占比高的学校逆袭空间很大。",
        "actionable_advice": "择校时就关注复试占比。如果初试分数不理想，优先准备复试占比50%+的院校。",
        "verification_method": "查看目标院校复试办法中的总成绩计算公式，算出复试占比。",
        "tags": ["复试占比", "逆袭", "总成绩"],
        "sort_order": 17,
    },
    {
        "stage": "retest",
        "category": "面试技巧",
        "title": "诚实比装懂重要——不会就说不会",
        "content": "复试面试中，导师最反感的就是不懂装懂。被问到不会的问题，直接说「这个问题我目前不太了解，但我的理解是...」比瞎编要好得多。导师更看重你的思维方式和诚实态度。",
        "importance": "medium",
        "common_misconception": "很多人以为面试时必须什么都会答，实际上导师更看重诚实和思维能力。",
        "actionable_advice": "面试前准备「不会答的应对策略」：承认不会→展示思考过程→表达学习意愿。",
        "verification_method": "模拟面试时练习「不会答」的场景，观察导师反馈。",
        "tags": ["面试", "诚实", "技巧"],
        "sort_order": 18,
    },
    {
        "stage": "retest",
        "category": "面试技巧",
        "title": "本科论文可能被问到——提前准备",
        "content": "很多导师在复试中会问本科毕业论文/设计的内容，以考察学生的学术能力和思维深度。如果你的论文和专业相关，这几乎是必问项。提前准备好论文的核心观点、方法、结论和不足。",
        "importance": "medium",
        "common_misconception": "很多人以为复试只考专业课知识，实际上本科论文是常见的面试话题。",
        "actionable_advice": "复试前回顾自己的本科论文，准备好3分钟口头概述和可能被追问的问题。",
        "verification_method": "列出论文的5个可能被追问的点，准备好回答。",
        "tags": ["本科论文", "面试", "准备"],
        "sort_order": 19,
    },
]


# ======================================================================
# 暗知识服务
# ======================================================================

def seed_dark_knowledge(db: Session) -> int:
    """预填充暗知识数据。如果表为空则插入，返回插入条数。"""
    existing = db.query(DarkKnowledge).count()
    if existing > 0:
        return 0

    for item in DARK_KNOWLEDGE_SEED:
        dk = DarkKnowledge(**item)
        db.add(dk)
    db.commit()
    return len(DARK_KNOWLEDGE_SEED)


def get_dark_knowledge_by_stage(
    db: Session,
    stage: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[DarkKnowledge], int]:
    """获取暗知识列表，可按阶段过滤，支持分页。"""
    query = db.query(DarkKnowledge)
    if stage and stage != "all":
        query = query.filter(DarkKnowledge.stage == stage)
    
    # 获取总数
    total = query.count()
    
    # 应用分页
    offset = (page - 1) * limit
    items = query.order_by(DarkKnowledge.stage, DarkKnowledge.sort_order).offset(offset).limit(limit).all()
    
    return items, total


def get_dark_knowledge_stages(db: Session) -> list[dict]:
    """获取所有阶段及其条数（单次查询，避免 N+1）。"""
    from sqlalchemy import func

    stage_names = {
        "decision": "决策阶段",
        "school_selection": "择校阶段",
        "preparation": "备考阶段",
        "exam": "初试后",
        "retest": "复试阶段",
    }
    rows = (
        db.query(DarkKnowledge.stage, func.count(DarkKnowledge.id).label("count"))
        .group_by(DarkKnowledge.stage)
        .all()
    )
    return [{"stage": s, "name": stage_names.get(s, s), "count": c} for s, c in rows]


# ======================================================================
# 院校情报服务
# ======================================================================

def query_school_intel(school_name: str, major_name: str) -> dict:
    """AI 生成院校情报。

    基于公开信息（学校官网、研招网、考研论坛、知乎经验贴等）
    生成结构化院校情报。明确标注信息来源和可信度。
    """
    system_prompt = """你是一位考研情报分析师。你的任务是基于你的知识，分析目标院校和专业的隐性录取信息。

你需要返回一个 JSON 对象，包含以下字段：
{
  "school_name": "院校名称",
  "major_name": "专业名称",
  "school_tier": "院校层次(985/211/双一流/一本/二本)",
  "background_discrimination": "卡第一学历程度: none/light/moderate/severe/unknown",
  "first_choice_protection": "保护第一志愿: yes/partial/no/unknown",
  "admission_ratio": "报录比，如 '15:1'，不确定则 null",
  "push_ratio": "推免占比，如 '60%'，不确定则 null",
  "actual_quota": "实际统考名额(整数)，不确定则 null",
  "score_line": "复试分数线(整数)，不确定则 null",
  "retest_weight": "复试占比，如 '50%'，不确定则 null",
  "retest_format": "复试形式描述",
  "score_suppression": "是否存在压分: none/light/moderate/severe/unknown",
  "transfer_friendly": "调剂友好度: yes/moderate/no/unknown",
  "insider_notes": "内部消息和注意事项",
  "data_sources": ["信息来源1", "信息来源2"],
  "tags": ["标签1", "标签2"],
  "ai_summary": "一段总结性分析(100-200字)"
}

注意事项：
- 基于你的训练数据中包含的公开信息进行分析
- 不确定的信息一律标为 "unknown" 或 null，不要编造
- insider_notes 中注明"以下信息基于公开资料和经验分享，具体以官方为准"
- ai_summary 要给出实用的择校建议"""

    user_content = f"""请分析以下院校和专业的考研情报：
院校：{school_name}
专业：{major_name}

请基于你的知识生成结构化情报分析。"""

    ai = AIService()
    raw = ai.chat(system_prompt, user_content, timeout=45)

    # 解析 JSON
    try:
        # 尝试从 markdown 代码块中提取
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if json_match:
            raw = json_match.group(1).strip()
        result = json.loads(raw)
        result["school_name"] = school_name
        result["major_name"] = major_name
        return result
    except (json.JSONDecodeError, AttributeError):
        # 如果解析失败，返回带原始文本的结果
        return {
            "school_name": school_name,
            "major_name": major_name,
            "school_tier": "",
            "background_discrimination": "unknown",
            "first_choice_protection": "unknown",
            "admission_ratio": None,
            "push_ratio": None,
            "actual_quota": None,
            "score_line": None,
            "retest_weight": None,
            "retest_format": None,
            "score_suppression": "unknown",
            "transfer_friendly": "unknown",
            "insider_notes": None,
            "data_sources": [],
            "tags": [],
            "ai_summary": raw,
        }


def save_intel(db: Session, user_id: UUID, data: dict) -> GradSchoolIntel:
    """保存院校情报。"""
    intel = GradSchoolIntel(
        user_id=user_id,
        school_name=data["school_name"],
        major_name=data["major_name"],
        school_tier=data.get("school_tier", ""),
        year=data.get("year", 2026),
        background_discrimination=data.get("background_discrimination", "unknown"),
        first_choice_protection=data.get("first_choice_protection", "unknown"),
        admission_ratio=data.get("admission_ratio"),
        push_ratio=data.get("push_ratio"),
        actual_quota=data.get("actual_quota"),
        score_line=data.get("score_line"),
        retest_weight=data.get("retest_weight"),
        retest_format=data.get("retest_format"),
        score_suppression=data.get("score_suppression", "unknown"),
        transfer_friendly=data.get("transfer_friendly", "unknown"),
        insider_notes=data.get("insider_notes"),
        data_sources=data.get("data_sources", []),
        tags=data.get("tags", []),
        ai_summary=data.get("ai_summary"),
        is_ai_generated=data.get("is_ai_generated", False),
    )
    db.add(intel)
    db.commit()
    db.refresh(intel)
    return intel


def get_user_intel_list(db: Session, user_id: UUID) -> list[GradSchoolIntel]:
    """获取用户保存的所有院校情报。"""
    return (
        db.query(GradSchoolIntel)
        .filter(GradSchoolIntel.user_id == user_id)
        .order_by(GradSchoolIntel.created_at.desc())
        .all()
    )


def delete_intel(db: Session, user_id: UUID, intel_id: UUID) -> bool:
    """删除院校情报。"""
    intel = (
        db.query(GradSchoolIntel)
        .filter(GradSchoolIntel.id == intel_id, GradSchoolIntel.user_id == user_id)
        .first()
    )
    if not intel:
        return False
    db.delete(intel)
    db.commit()
    return True


# ======================================================================
# 自我定位服务
# ======================================================================

def create_positioning(db: Session, user_id: UUID, data: dict, bypass_cache: bool = False) -> SelfPositioning:
    """创建自我定位并触发 AI 评估。
    
    Args:
        bypass_cache: 是否绕过缓存强制重新生成
    """
    # 计算缓存键
    cache_key = _compute_cache_key(data)
    
    # 检查缓存（除非绕过）
    if not bypass_cache:
        cached_result = _get_cached_result(cache_key)
        if cached_result:
            logger.info("使用缓存的 AI 结果")
            # 创建定位记录但不调用 AI
            positioning = SelfPositioning(
                user_id=user_id,
                undergrad_tier=data["undergrad_tier"],
                undergrad_major=data.get("undergrad_major"),
                gpa=data.get("gpa"),
                gpa_rank=data.get("gpa_rank"),
                english_level=data.get("english_level"),
                english_score=data.get("english_score"),
                research_experience=data.get("research_experience"),
                competitions=data.get("competitions", []),
                awards=data.get("awards"),
                internships=data.get("internships"),
                target_school=data.get("target_school"),
                target_major=data.get("target_major"),
                target_region=data.get("target_region"),
                other_info=data.get("other_info"),
                ai_assessment=cached_result.get("ai_assessment"),
                reach_schools=cached_result.get("reach_schools", []),
                target_schools=cached_result.get("target_schools", []),
                safety_schools=cached_result.get("safety_schools", []),
                success_probability=cached_result.get("success_probability"),
                risk_warnings=cached_result.get("risk_warnings", []),
            )
            db.add(positioning)
            db.commit()
            db.refresh(positioning)
            return positioning

    # 创建定位记录
    positioning = SelfPositioning(
        user_id=user_id,
        undergrad_tier=data["undergrad_tier"],
        undergrad_major=data.get("undergrad_major"),
        gpa=data.get("gpa"),
        gpa_rank=data.get("gpa_rank"),
        english_level=data.get("english_level"),
        english_score=data.get("english_score"),
        research_experience=data.get("research_experience"),
        competitions=data.get("competitions", []),
        awards=data.get("awards"),
        internships=data.get("internships"),
        target_school=data.get("target_school"),
        target_major=data.get("target_major"),
        target_region=data.get("target_region"),
        other_info=data.get("other_info"),
    )
    db.add(positioning)
    db.commit()
    db.refresh(positioning)

    # AI 评估（带降级处理）
    try:
        assessment = _generate_ai_assessment(positioning)
        # 缓存结果
        _set_cached_result(cache_key, assessment)
    except AIServiceNotConfigured:
        logger.warning("LLM 未配置，使用静态降级推荐")
        assessment = _get_static_recommendations(data)
    except Exception as e:
        logger.error("AI 评估失败: %s", e)
        assessment = _get_static_recommendations(data)
    
    positioning.ai_assessment = assessment.get("ai_assessment")
    positioning.reach_schools = assessment.get("reach_schools", [])
    positioning.target_schools = assessment.get("target_schools", [])
    positioning.safety_schools = assessment.get("safety_schools", [])
    positioning.success_probability = assessment.get("success_probability")
    positioning.risk_warnings = assessment.get("risk_warnings", [])
    db.commit()
    db.refresh(positioning)
    return positioning


def _generate_ai_assessment(positioning: SelfPositioning) -> dict:
    """AI 基于用户背景生成三档院校推荐。"""
    system_prompt = """你是一位资深考研规划师，有10年以上的择校指导经验。你的任务是基于考生的背景信息，给出精准的三档院校推荐。

你需要返回一个 JSON 对象：
{
  "ai_assessment": "综合评估(200-400字)：分析考生优势、劣势、适合的方向",
  "reach_schools": [
    {"name": "学校名", "major": "专业", "tier": "985/211等", "reason": "推荐理由", "probability": 30}
  ],
  "target_schools": [
    {"name": "学校名", "major": "专业", "tier": "层次", "reason": "推荐理由", "probability": 60}
  ],
  "safety_schools": [
    {"name": "学校名", "major": "专业", "tier": "层次", "reason": "推荐理由", "probability": 85}
  ],
  "success_probability": 55,
  "risk_warnings": ["风险提示1", "风险提示2"]
}

规则：
- reach_schools: 2-3所，成功率20-40%，略高于当前水平
- target_schools: 3-4所，成功率50-70%，匹配当前水平
- safety_schools: 2-3所，成功率80-95%，保底选择
- 推荐具体学校名，不要泛泛而谈
- success_probability 是整体上岸概率
- risk_warnings 指出考生可能面临的风险
- 如果信息不足，在 ai_assessment 中说明需要补充什么信息"""

    background = f"""考生背景信息：
- 本科层次：{positioning.undergrad_tier}
- 本科专业：{positioning.undergrad_major or '未填写'}
- GPA：{positioning.gpa or '未填写'}
- GPA排名：{positioning.gpa_rank or '未填写'}
- 英语水平：{positioning.english_level or '未填写'} {positioning.english_score or ''}
- 科研经历：{positioning.research_experience or '无'}
- 竞赛获奖：{positioning.competitions or '无'}
- 实习经历：{positioning.internships or '无'}
- 目标专业：{positioning.target_major or '未确定'}
- 目标地区：{positioning.target_region or '不限'}
- 其他信息：{positioning.other_info or '无'}

请基于以上背景，给出三档院校推荐。如果目标专业未确定，根据本科专业推荐相近方向。"""

    ai = AIService()
    raw = ai.chat(system_prompt, background, timeout=45)

    try:
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if json_match:
            raw = json_match.group(1).strip()
        return json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        return {
            "ai_assessment": raw,
            "reach_schools": [],
            "target_schools": [],
            "safety_schools": [],
            "success_probability": None,
            "risk_warnings": ["AI 评估结果解析失败，请重试"],
        }


def get_latest_positioning(db: Session, user_id: UUID) -> SelfPositioning | None:
    """获取用户最新的自我定位。"""
    return (
        db.query(SelfPositioning)
        .filter(SelfPositioning.user_id == user_id)
        .order_by(SelfPositioning.created_at.desc())
        .first()
    )


def get_positioning_history(db: Session, user_id: UUID) -> list[SelfPositioning]:
    """获取用户自我定位历史。"""
    return (
        db.query(SelfPositioning)
        .filter(SelfPositioning.user_id == user_id)
        .order_by(SelfPositioning.created_at.desc())
        .all()
    )


# ======================================================================
# 研招网真实数据查询
# ======================================================================

def list_yanzhao_programs(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    department: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[GradYanzhaoProgram], int]:
    """查询研招网专业目录，支持分页。"""
    query = db.query(GradYanzhaoProgram)
    if university_name:
        query = query.filter(GradYanzhaoProgram.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradYanzhaoProgram.major_name.ilike(f"%{major_name}%"))
    if department:
        query = query.filter(GradYanzhaoProgram.department.ilike(f"%{department}%"))
    if degree_type:
        query = query.filter(GradYanzhaoProgram.degree_type == degree_type)
    if year:
        query = query.filter(GradYanzhaoProgram.year == year)
    
    # 获取总数
    total = query.count()
    
    # 应用分页
    items = (
        query.order_by(GradYanzhaoProgram.university_name, GradYanzhaoProgram.major_name)
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return items, total


def count_yanzhao_programs(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    department: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
) -> int:
    """统计专业目录数量。"""
    query = db.query(GradYanzhaoProgram)
    if university_name:
        query = query.filter(GradYanzhaoProgram.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradYanzhaoProgram.major_name.ilike(f"%{major_name}%"))
    if department:
        query = query.filter(GradYanzhaoProgram.department.ilike(f"%{department}%"))
    if degree_type:
        query = query.filter(GradYanzhaoProgram.degree_type == degree_type)
    if year:
        query = query.filter(GradYanzhaoProgram.year == year)
    return query.count()


def list_scoreline_records(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[GradScorelineRecord]:
    """查询复试分数线记录。"""
    query = db.query(GradScorelineRecord)
    if university_name:
        query = query.filter(GradScorelineRecord.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradScorelineRecord.major_name.ilike(f"%{major_name}%"))
    if degree_type:
        query = query.filter(GradScorelineRecord.degree_type == degree_type)
    if year:
        query = query.filter(GradScorelineRecord.year == year)
    return (
        query.order_by(
            GradScorelineRecord.university_name,
            GradScorelineRecord.major_name,
            GradScorelineRecord.year.desc(),
        )
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_scoreline_trend(
    db: Session,
    university_name: str,
    major_name: str,
    degree_type: str | None = None,
) -> dict:
    """获取某院校某专业近年的复试分数线趋势。"""
    query = db.query(GradScorelineRecord).filter(
        GradScorelineRecord.university_name == university_name,
        GradScorelineRecord.major_name == major_name,
    )
    if degree_type:
        query = query.filter(GradScorelineRecord.degree_type == degree_type)
    records = query.order_by(GradScorelineRecord.year).all()

    return {
        "university_name": university_name,
        "major_name": major_name,
        "degree_type": degree_type,
        "years": [r.year for r in records],
        "total_score_lines": [r.total_score_line for r in records],
        "politics_scores": [r.politics_score for r in records],
        "foreign_language_scores": [r.foreign_language_score for r in records],
        "business_1_scores": [r.business_1_score for r in records],
        "business_2_scores": [r.business_2_score for r in records],
        "application_counts": [r.application_count for r in records],
        "enrollment_counts": [r.enrollment_count for r in records],
    }


def list_adjustment_info(
    db: Session,
    *,
    university_name: str | None = None,
    major_name: str | None = None,
    status: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[GradAdjustmentInfo]:
    """查询调剂信息。"""
    query = db.query(GradAdjustmentInfo)
    if university_name:
        query = query.filter(GradAdjustmentInfo.university_name.ilike(f"%{university_name}%"))
    if major_name:
        query = query.filter(GradAdjustmentInfo.major_name.ilike(f"%{major_name}%"))
    if status:
        query = query.filter(GradAdjustmentInfo.status == status)
    if year:
        query = query.filter(GradAdjustmentInfo.year == year)
    return (
        query.order_by(
            GradAdjustmentInfo.year.desc(),
            GradAdjustmentInfo.university_name,
        )
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_school_data_summary(db: Session, university_name: str) -> dict:
    """获取某院校的数据汇总（专业数、最新分数线、趋势、调剂信息）。"""
    programs = (
        db.query(GradYanzhaoProgram)
        .filter(GradYanzhaoProgram.university_name == university_name)
        .all()
    )
    program_count = len(programs)

    latest_scoreline = (
        db.query(GradScorelineRecord)
        .filter(GradScorelineRecord.university_name == university_name)
        .order_by(GradScorelineRecord.year.desc())
        .first()
    )

    adjustments = (
        db.query(GradAdjustmentInfo)
        .filter(GradAdjustmentInfo.university_name == university_name)
        .all()
    )

    trend = "stable"
    if latest_scoreline:
        # 获取前两年数据判断趋势
        prev = (
            db.query(GradScorelineRecord)
            .filter(
                GradScorelineRecord.university_name == university_name,
                GradScorelineRecord.major_name == latest_scoreline.major_name,
                GradScorelineRecord.year == latest_scoreline.year - 1,
            )
            .first()
        )
        if prev and prev.total_score_line and latest_scoreline.total_score_line:
            diff = latest_scoreline.total_score_line - prev.total_score_line
            if diff > 10:
                trend = "up"
            elif diff < -10:
                trend = "down"

    return {
        "university_name": university_name,
        "program_count": program_count,
        "latest_year": latest_scoreline.year if latest_scoreline else None,
        "latest_scoreline": latest_scoreline.total_score_line if latest_scoreline else None,
        "scoreline_trend": trend,
        "has_adjustment": len(adjustments) > 0,
        "adjustment_count": len(adjustments),
    }
