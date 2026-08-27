"""家庭对话脚手架服务层 — 理解父母 + 准备论据 + 模拟对话练习。

设计理念：不是「听父母话」或「反抗父母」，而是「翻译」——
把父母旧时代经验翻译成新时代语境，提供话术模板 + 数据化回应 + 模拟对话练习。

三层结构：
1. 理解父母 — 分析父母为什么这么想、时代背景、合理部分
2. 准备弹药 — 生成 3-5 个 Argument（含父母话术/建议回应/数据支撑/共情提示）+ 沟通技巧
3. 实战演练 — 模拟父母视角回复用户的话

LLM 调用可选：未配置 LLM_API_KEY 时使用预设模板生成。
"""

import json
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models.family_dialogue import FamilyDialogueSession

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 父母类型定义
# ----------------------------------------------------------------------
PARENT_ARCHETYPE_LABELS = {
    "stability_first": "稳定优先型",
    "prestige_first": "面子优先型",
    "practical_worry": "现实焦虑型",
    "supportive": "开明支持型",
}

PARENT_ARCHETYPE_SAYINGS = {
    "stability_first": "考公稳定，不用担心失业",
    "prestige_first": "公务员有面子，说出去好听",
    "practical_worry": "现在经济不好，先求稳",
    "supportive": "你自己决定，但要考虑清楚",
}


# ----------------------------------------------------------------------
# 场景识别 — 根据用户选择/父母担忧关键词匹配预设场景
# ----------------------------------------------------------------------
_SCENARIO_KEYWORDS = {
    "internet_vs_civil": [
        "互联网",
        "大厂",
        "字节",
        "腾讯",
        "阿里",
        "程序员",
        "开发",
        "前端",
        "后端",
        "算法",
        "产品经理",
        "技术",
    ],
    "kaoyan_vs_employment": ["考研", "研究生", "读研", "硕士", "保研"],
    "abroad_vs_domestic": ["留学", "出国", "海外", "美国", "英国", "港校"],
    "startup_vs_employment": ["创业", "自己干", "合伙"],
    "liberal_arts_transition": ["文科", "转行", "跨专业", "中文", "历史", "哲学"],
}


def _detect_scenario(user_choice: str, parent_concern: str) -> str:
    """根据用户选择和父母担忧的文本匹配预设场景。"""
    text = f"{user_choice} {parent_concern}"
    for scenario, keywords in _SCENARIO_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return scenario
    return "internet_vs_civil"  # 默认走最常见场景


# ----------------------------------------------------------------------
# 真实数据支撑（可引用）
# ----------------------------------------------------------------------
_DATA = {
    "civil_salary": "一线城市科员年综合收入约 15-25 万（含公积金、津贴），三四线城市约 8-15 万（来源：各地公务员公开招录待遇说明）",
    "civil_competition": "2024 年国考报名约 303 万，招录约 3.96 万，整体报录比约 76:1，热门岗位可达数千比一（来源：国家公务员局）",
    "civil_stability": "公务员编制稳定，但 2019 年公务员法修订后引入「能上能下」机制，并非绝对不失业",
    "internet_salary": "2024 届应届生头部大厂 SP/SSP offer 年薪 30-45 万，普通本科应届 15-25 万（来源：各大厂校招公开薪资带 + 牛客网统计）",
    "internet_layoff": "2022-2023 年互联网行业优化较多，但头部公司应届生招聘仍在持续；2024 年起逐步回暖（来源：脉脉、Boss 直聘年报）",
    "internet_growth": "互联网 3-5 年经验工程师薪资可达 40-80 万，成长曲线陡峭；但 35 岁后存在职业天花板争议",
    "kaoyan_competition": "2024 年考研报名 438 万，录取约 130 万，整体报录比约 3.4:1（来源：教育部）",
    "kaoyan_salary_premium": "硕士起薪比本科平均高 30-50%，但需投入 2-3 年时间成本，机会成本约 20-40 万",
    "abroad_cost": "美国硕士 1-2 年总成本约 60-120 万人民币，英国 30-60 万（来源：各校学费 + 生活费估算）",
    "abroad_roi": "留学回国起薪平均比国内同层次高 20-40%，但回本周期 5-8 年；海归光环正在减弱（来源：智联招聘海归报告）",
    "startup_failure": "中国初创公司 3 年存活率约 10%，大学生创业成功率更低（来源：国家统计局）",
    "liberal_arts_salary": "文科应届生平均起薪 6-9k/月，转行互联网/数据方向后 1-2 年可达 12-20k（来源：麦可思就业报告）",
}


# ----------------------------------------------------------------------
# 场景预设论据 — 每个场景一组 Argument 模板
# ----------------------------------------------------------------------
# 每条 Argument: parent_saying / user_response / data_backing / empathy_note
_SCENARIO_ARGUMENTS: dict[str, list[dict]] = {
    "internet_vs_civil": [
        {
            "parent_saying": "考公稳定，不用担心失业，铁饭碗多好。",
            "user_response": "爸妈，我理解你们看重稳定。其实现在互联网大厂也有完善的福利和长期激励，而且我年轻的时候多闯一闯，能力积累快，3 年后的选择面反而更广。我可以先去互联网试 2-3 年，如果真不行，再考公也来得及。",
            "data_backing": f"{_DATA['internet_salary']}；{_DATA['civil_salary']}。互联网 3 年经验后转行/跳槽空间更大。",
            "empathy_note": "先肯定父母「为你好」的出发点，再说明「年轻是试错资本」，把稳定和闯荡用「先试后转」折中。",
        },
        {
            "parent_saying": "互联网天天裁员，哪天就被裁了，多没安全感。",
            "user_response": "裁员确实存在，但裁员主要影响业绩不达标的岗位，应届生有保护期。而且我会持续学核心技术，技术过硬的人在哪都吃香。反过来说，公务员也不是绝对不失业，2019 年修法后也有退出机制。",
            "data_backing": f"{_DATA['internet_layoff']}；{_DATA['civil_stability']}。",
            "empathy_note": "承认风险存在，但用「能力护城河」化解焦虑，避免硬怼「公务员也会下岗」。",
        },
        {
            "parent_saying": "公务员有面子，说出去亲戚朋友都羡慕。",
            "user_response": "面子是上一代的评价标准。现在年轻一代更看重大厂背书、技术能力和收入。我在字节/腾讯做技术，说出去大家一样认可。而且面子换不来我每天 8 小时的快乐，我更想做喜欢的事。",
            "data_backing": f"{_DATA['internet_salary']}，头部大厂 offer 在同龄人里属于高薪第一梯队，社会认可度同样高。",
            "empathy_note": "不要否定父母的面子观，而是用「新一代的评价体系」做替代，提供新的骄傲点。",
        },
        {
            "parent_saying": "现在经济不好，先求稳，等形势好了再折腾。",
            "user_response": "正因为经济周期波动，才更应该在年轻时有抗风险能力。互联网虽然波动大，但上行时的收益也大；公务员稳定但涨幅有限。我可以给自己 3 年时间，攒一笔钱和能力，进可攻退可守。",
            "data_backing": f"{_DATA['internet_salary']} vs {_DATA['civil_salary']}，互联网 3 年可攒下公务员 5-6 年的积蓄，提供转型缓冲。",
            "empathy_note": "把「求稳」重新定义为「攒筹码」，与父母的「稳」目标一致，只是路径不同。",
        },
        {
            "parent_saying": "考公上岸多体面，家里也有关系能帮你。",
            "user_response": "爸妈谢谢你们替我铺路。但考公岗位我未必喜欢，每天做自己不喜欢的事很痛苦。互联网行业我能学到真本事，这些能力是我自己的，谁也拿不走。我想先靠自己试一试。",
            "data_backing": "互联网行业技能可迁移性强（编程、产品、数据能力跨行业通用），而公务员能力相对行业专属。",
            "empathy_note": "感谢父母的资源投入，但表达「靠自己」的独立意愿，避免让父母觉得被否定。",
        },
    ],
    "kaoyan_vs_employment": [
        {
            "parent_saying": "现在本科生找不到好工作，还是考研稳妥。",
            "user_response": "爸妈，我查过数据，确实有些岗位要硕士，但我目标行业更看项目经验。我可以先就业攒经验，2-3 年后如果想读在职研究生也来得及，工作经验 + 学历比纯学历更值钱。",
            "data_backing": f"{_DATA['kaoyan_salary_premium']}；互联网/技术岗更看重项目经验与作品集。",
            "empathy_note": "承认学历贬值是事实，但用「经验 + 在职学历」组合拳给父母一个折中方案。",
        },
        {
            "parent_saying": "考研出来起点更高，何必现在去吃苦。",
            "user_response": "考研也有成本，2-3 年时间 + 机会成本约 20-40 万，而且考研越来越卷，今年报录比 3.4:1。我现在直接就业能早 3 年积累经验和人脉，3 年后我可能已经是带团队的人了。",
            "data_backing": f"{_DATA['kaoyan_competition']}；3 年工作经验在多数行业价值 ≥ 硕士学历。",
            "empathy_note": "用「时间成本」量化考研代价，让父母看到「现在就业」不是退而求其次，而是另一条路。",
        },
        {
            "parent_saying": "家里不差钱，你安心读书考研就行。",
            "user_response": "谢谢爸妈支持。但我想先工作试试，不是因为家里差钱，而是想早点知道自己到底适合什么。读研方向选错了更浪费，先就业能帮我更精准地选未来的方向。",
            "data_backing": "工作 1-2 年后再读研，目标更清晰，留学/考研申请成功率更高，且能选对口方向。",
            "empathy_note": "把「先工作」包装成「为更好的读研做准备」，与父母「读书」的期待对齐。",
        },
        {
            "parent_saying": "考研失败怎么办？现在就两条腿走路。",
            "user_response": "我可以做一个时间表：3-6 月全力准备考研，同时保持 1-2 个备选 offer。如果考研上岸就去读，没上岸直接就业，不浪费一年。这样既兼顾你们的期望，也有兜底。",
            "data_backing": f"{_DATA['kaoyan_competition']}，两手准备可降低单一路径风险。",
            "empathy_note": "用「双轨计划」回应焦虑，给父母确定性，比单纯「我不考研」更容易接受。",
        },
    ],
    "abroad_vs_domestic": [
        {
            "parent_saying": "留学花那么多钱，什么时候能挣回来？",
            "user_response": "爸妈，留学成本确实高，美国 60-120 万、英国 30-60 万。但海归起薪平均高 20-40%，5-8 年能回本。更重要的是留学带来的视野、语言和人脉，这些是长期资产，不只是算工资。",
            "data_backing": f"{_DATA['abroad_cost']}；{_DATA['abroad_roi']}。",
            "empathy_note": "用「长期资产」概念补足纯工资回报的短板，承认回本周期长。",
        },
        {
            "parent_saying": "国内读研也不错，何必跑那么远。",
            "user_response": "国内考研越来越卷，报录比 3.4:1，而海外申请制能同时申多所学校，机会更多。而且我想学的方向国外确实更强，回来后有差异化优势。我会认真选校，控制预算。",
            "data_backing": f"{_DATA['kaoyan_competition']}；海外申请可同时投递多校，录取概率更高。",
            "empathy_note": "用「申请制 vs 考试制」的客观差异说明留学机会成本更低，而非贬低国内。",
        },
        {
            "parent_saying": "国外不安全，一个人在外多辛苦。",
            "user_response": "我会选治安好的国家和城市，也提前做好安全准备。辛苦是真的，但这是成长必经的独立过程。现在通讯方便，我每周和你们视频，不会让你们担心。",
            "data_backing": "主流留学国家（英、美、加、澳、新）治安总体可控，学校有完善国际生支持体系。",
            "empathy_note": "正面回应父母的情感担忧（安全、孤独），给出具体的安心措施。",
        },
        {
            "parent_saying": "现在海归也不吃香了，回来一样找不到工作。",
            "user_response": "海归光环确实在减弱，但顶尖院校回来竞争力依然强。关键是选对学校和专业，不是为留学而留学。我会申排名和就业率都好的项目，回来有明确目标，不会盲目。",
            "data_backing": f"{_DATA['abroad_roi']}，名校海归仍有显著溢价，普通院校海归优势下降。",
            "empathy_note": "承认「海归贬值」是事实，但用「选校策略」回应，体现成熟度。",
        },
    ],
    "startup_vs_employment": [
        {
            "parent_saying": "创业风险太大，九死一生，别折腾。",
            "user_response": "爸妈，创业确实风险高，3 年存活率约 10%。但我想先去成熟公司工作 2-3 年，攒经验、人脉和启动资金，再考虑创业。现在直接创业我也没把握。",
            "data_backing": f"{_DATA['startup_failure']}；先就业积累资源再创业，成功率更高。",
            "empathy_note": "把「创业」延后为「先就业后创业」，与父母「先求稳」的诉求一致。",
        },
        {
            "parent_saying": "稳定工作不好吗？非要冒险。",
            "user_response": "我理解你们希望我安稳。但我心里确实有创业的想法，压抑着会一直遗憾。我可以给创业设个「止损线」：攒够 50 万启动资金 + 2 年经验才动手，失败也只损失时间和本金，不影响基本生活。",
            "data_backing": "设定明确止损线（资金 + 时间）可显著降低创业对家庭的影响。",
            "empathy_note": "用「止损线」给父母安全感，证明你不是冲动。",
        },
        {
            "parent_saying": "你一个大学生懂什么创业？",
            "user_response": "所以我现在不会贸然创业。我想先去行业头部公司工作，学习他们的打法，同时业余做小项目验证想法。等真的跑通了 MVP 再全职，这样最稳妥。",
            "data_backing": "先业余 MVP 验证再全职，是 Y Combinator 等顶级孵化器推荐路径，成功率更高。",
            "empathy_note": "用「学习 + 验证」回应「不懂」的质疑，体现谦逊和务实。",
        },
    ],
    "liberal_arts_transition": [
        {
            "parent_saying": "你学中文的，转行互联网能行吗？专业都白学了。",
            "user_response": "爸妈，文科专业培养的表达、分析和审美，在互联网产品、运营、内容方向反而很吃香。我会用半年学技术工具，加上我原有的文字能力，做内容运营/产品策划有差异化优势。",
            "data_backing": f"{_DATA['liberal_arts_salary']}，文科转行互联网/数据后薪资涨幅显著。",
            "empathy_note": "把「专业白学」重新定义为「能力迁移」，用差异化优势回应。",
        },
        {
            "parent_saying": "文科考公务员多对口，为什么要去互联网受罪？",
            "user_response": "文科考公确实对口，但竞争极激烈，76:1 的报录比，而且岗位多为基层。互联网节奏快但成长快，1-2 年薪资就能翻倍。我想趁年轻先拼一下，3 年后如果不行再考公也来得及。",
            "data_backing": f"{_DATA['civil_competition']}；{_DATA['liberal_arts_salary']}。",
            "empathy_note": "用「时间窗口」论给父母安全感，把考公作为兜底而非首选。",
        },
        {
            "parent_saying": "转行没人带，你一个人摸黑多难。",
            "user_response": "所以我会先找培训课程 + 加入转行社群，再找个前辈带。现在网上转行成功的文科生很多，我会主动学习他们的路径。先业余 3 个月试水，跑通再全职。",
            "data_backing": "结构化学习路径（课程 + 社群 + 导师 + 业余试水）可显著降低转行失败率。",
            "empathy_note": "用「方法论」回应「没人带」的担忧，体现有计划而非冲动。",
        },
        {
            "parent_saying": "稳定点不好吗，非要去卷。",
            "user_response": "我理解你们希望我安稳。但文科传统岗位薪资天花板低，6-9k 起薪涨得慢。我想趁还没成家，先去高成长行业拼 3 年，攒一笔钱和能力，进可攻退可守。",
            "data_backing": f"{_DATA['liberal_arts_salary']}，传统文科岗 5 年薪资涨幅有限。",
            "empathy_note": "用「家庭责任窗口」论（还没成家）说明现在是闯荡最佳时机。",
        },
    ],
}


# ----------------------------------------------------------------------
# 理解父母 — 不同父母类型的分析模板
# ----------------------------------------------------------------------
_UNDERSTANDING_TEMPLATES = {
    "stability_first": (
        "父母属于「稳定优先型」。他们这么想有深刻的时代背景：他们成长的年代\n"
        "经历过下岗潮、经济转型，亲眼见过「不稳定」带来的恐慌，所以把「铁饭碗」\n"
        "视为最高安全感。他们的担忧是真实的，也是出于爱。\n\n"
        "合理部分：稳定确实是幸福的基础，尤其在不确定的时代。\n"
        "需要翻译的部分：他们眼里的「稳定 = 体制内」，而你这一代的「稳定」\n"
        "更可能是「能力护城河 + 多元收入」。沟通时不要否定稳定，而是讨论\n"
        "「什么样的稳定更可持续」。"
    ),
    "prestige_first": (
        "父母属于「面子优先型」。在他们成长的年代，社会评价高度依赖身份标签，\n"
        "「公务员」「老师」「医生」是体面的代名词，说出去能让亲戚高看一眼。\n"
        "这种面子观背后，是他们对「被认可」的渴望，也是社交安全感。\n\n"
        "合理部分：社会认可确实影响幸福感和资源获取。\n"
        "需要翻译的部分：新一代的评价体系已经多元，大厂、创业、专业能力\n"
        "同样能带来认可。沟通时可以提供新的「骄傲点」，而非否定面子。"
    ),
    "practical_worry": (
        "父母属于「现实焦虑型」。他们对经济周期、就业形势敏感，可能亲眼见过\n"
        "亲友失业或创业失败，所以倾向于「先求稳」。这种焦虑是经验的产物，\n"
        "并非无的放矢。\n\n"
        "合理部分：经济下行期确实应该谨慎，现金流为王。\n"
        "需要翻译的部分：他们的「稳」是「不动作」，而你这一代的「稳」是\n"
        "「动作 + 风险控制」。沟通时用「止损线」「兜底方案」回应焦虑，\n"
        "证明你不是冲动。"
    ),
    "supportive": (
        "父母属于「开明支持型」。他们愿意尊重你的选择，但会担心你想不清楚。\n"
        "这类父母往往是你最坚实的后盾，沟通成本最低。\n\n"
        "合理部分：他们的「考虑清楚」是真心的，希望你对自己的选择负责。\n"
        "需要翻译的部分：把你的选择结构化呈现——目标、路径、风险、兜底，\n"
        "让他们看到你的成熟，他们会更放心地支持你。"
    ),
}


# ----------------------------------------------------------------------
# 沟通技巧 — 通用模板
# ----------------------------------------------------------------------
_TALKING_TIPS = [
    "先共情再表态：「我理解你们是为我好」开头，降低防御。",
    "用「我们」而非「我」：把决策包装成家庭共同决策，而非个人对抗。",
    "数据要落地：引用具体数字和来源，比空谈「前景好」更有说服力。",
    "提供折中方案：不要二选一，给「先试 X 个月/Y 年，不行再转」的过渡路径。",
    "讲自己的思考过程：父母更担心你「想不清楚」而非「选错了」。",
    "选对时机：饭后散步、心情好时谈，避免饭桌上或睡前争吵。",
    "分多次沟通：一次谈不完没关系，给彼此消化的时间，不要逼对方当场表态。",
    "邀请第三方：让父母信任的亲戚/老师/学长帮你说一句，胜过你说十句。",
]


# ----------------------------------------------------------------------
# start_session: 启动一次家庭对话脚手架会话
# ----------------------------------------------------------------------
def start_session(db: Session, user_id, data: dict) -> FamilyDialogueSession:
    """启动家庭对话脚手架会话。

    1. 识别场景（基于用户选择关键词）
    2. 生成「理解父母」分析
    3. 生成 3-5 个 Argument（含父母话术/建议回应/数据支撑/共情提示）
    4. 生成沟通技巧列表
    5. 持久化会话并返回
    """
    parent_concern = data["parent_concern"]
    user_choice = data["user_choice"]
    archetype = data.get("parent_archetype") or "stability_first"

    scenario = _detect_scenario(user_choice, parent_concern)

    # 生成理解分析（LLM 可选，模板兜底）
    understanding = _generate_understanding(archetype, parent_concern, user_choice, scenario)

    # 生成论据（LLM 可选，模板兜底）
    arguments = _generate_arguments(archetype, scenario, parent_concern, user_choice)

    # 沟通技巧
    talking_tips = list(_TALKING_TIPS)

    session = FamilyDialogueSession(
        user_id=user_id,
        parent_concern=parent_concern,
        user_choice=user_choice,
        parent_archetype=archetype,
        understanding=understanding,
        prepared_arguments=arguments,
        talking_tips=talking_tips,
        practice_messages=[],
        status="preparing",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _generate_understanding(
    archetype: str, parent_concern: str, user_choice: str, scenario: str
) -> str:
    """生成「理解父母」分析文本。LLM 可选，模板兜底。"""
    if settings.LLM_API_KEY:
        try:
            import asyncio

            text = asyncio.run(
                _generate_understanding_via_llm(archetype, parent_concern, user_choice)
            )
            if text:
                return text
        except Exception as e:
            logger.warning("LLM 生成理解分析失败，回退到模板: %s", e)

    template = _UNDERSTANDING_TEMPLATES.get(archetype, _UNDERSTANDING_TEMPLATES["stability_first"])
    return f"【父母担忧】{parent_concern}\n" f"【你的选择】{user_choice}\n\n" f"{template}"


async def _generate_understanding_via_llm(
    archetype: str, parent_concern: str, user_choice: str
) -> str:
    """用 LLM 生成个性化的「理解父母」分析。"""
    from app.services.ai_orchestrator import AIOrchestrator

    archetype_label = PARENT_ARCHETYPE_LABELS.get(archetype, archetype)
    system_prompt = (
        "你是一位家庭沟通调解师，擅长把父母的旧时代经验翻译成新时代语境。"
        "请分析父母为什么这么想、他们的时代背景、合理的部分、需要翻译的部分。"
        "语气要共情、客观，不偏袒任何一方。输出纯文本，200-400 字。"
    )
    user_prompt = (
        f"父母类型：{archetype_label}\n" f"父母担忧：{parent_concern}\n" f"用户选择：{user_choice}"
    )
    orchestrator = AIOrchestrator()
    return await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_prompt, timeout=30)


def _generate_arguments(
    archetype: str, scenario: str, parent_concern: str, user_choice: str
) -> list[dict]:
    """生成 3-5 个 Argument。LLM 可选，模板兜底。"""
    if settings.LLM_API_KEY:
        try:
            import asyncio

            args = asyncio.run(_generate_arguments_via_llm(archetype, parent_concern, user_choice))
            if args and len(args) >= 3:
                return args
        except Exception as e:
            logger.warning("LLM 生成论据失败，回退到模板: %s", e)

    # 模板：取场景预设论据（已含 4-5 条），保证至少 3 条
    base = list(_SCENARIO_ARGUMENTS.get(scenario, _SCENARIO_ARGUMENTS["internet_vs_civil"]))
    return base[:5]


async def _generate_arguments_via_llm(
    archetype: str, parent_concern: str, user_choice: str
) -> list[dict]:
    """用 LLM 生成个性化论据。"""
    from app.services.ai_orchestrator import AIOrchestrator

    archetype_label = PARENT_ARCHETYPE_LABELS.get(archetype, archetype)
    system_prompt = (
        "你是一位家庭沟通调解师。请针对父母的担忧和用户的选择，生成 3-5 条论据，"
        "每条包含：parent_saying（父母可能说的话）、user_response（建议回应）、"
        "data_backing（数据支撑，要具体可引用）、empathy_note（共情提示）。"
        "严格输出 JSON 数组（不要 markdown），结构：\n"
        '[{"parent_saying":"","user_response":"","data_backing":"","empathy_note":""}]'
    )
    user_prompt = (
        f"父母类型：{archetype_label}\n父母担忧：{parent_concern}\n用户选择：{user_choice}"
    )
    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_prompt, timeout=30)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []
    normalized = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not all(
            k in item for k in ("parent_saying", "user_response", "data_backing", "empathy_note")
        ):
            continue
        normalized.append(
            {
                "parent_saying": str(item["parent_saying"]),
                "user_response": str(item["user_response"]),
                "data_backing": str(item["data_backing"]),
                "empathy_note": str(item["empathy_note"]),
            }
        )
    return normalized


# ----------------------------------------------------------------------
# practice_reply: 模拟父母视角回复用户的话
# ----------------------------------------------------------------------
# 按父母类型的预设回复模板（轮换使用，避免重复）
_PRACTICE_REPLIES: dict[str, list[str]] = {
    "stability_first": [
        "你这孩子，怎么就不听呢？考公多好，铁饭碗，不用担心下岗。"
        "你看你张叔叔家孩子，考上公务员后日子多安稳。",
        "互联网今天招人明天裁人，哪有铁饭碗踏实？" "我们吃过的盐比你吃过的米多，听爸妈的没错。",
        "你说的我也听不太懂，我就问你一句：万一被裁了，你怎么办？" "你能保证一辈子不失业吗？",
        "行，那你说个期限。先去互联网试几年，几年？到时候不行必须考公，" "这是底线，你能答应吗？",
    ],
    "prestige_first": [
        "公务员说出去多好听，亲戚问起来爸妈也有面子。"
        "你在大公司打工，说出去人家还以为是流水线工人。",
        "面子值几个钱？你不懂，人活一张脸。" "你考上了公务员，全家都跟着光彩。",
        "你表哥考上选调生，过年回来多风光。" "你在大厂再厉害，亲戚们也不知道你在干啥。",
        "好，那你说说，你那个工作说出去怎么跟亲戚介绍？" "能让爸妈骄傲地跟人说吗？",
    ],
    "practical_worry": [
        "现在经济这么差，你看新闻没？大厂都在裁员。" "这时候去互联网，不是往火坑里跳吗？",
        "我们不是不支持你，是真的担心。家里也不富裕，" "你万一失业了，我们帮不上忙，你怎么办？",
        "考公至少旱涝保收。你现在年轻不懂，等你有房贷有孩子，" "就知道稳定有多重要了。",
        "你说的止损线我听懂了，但万一呢？我们这把年纪了，" "经不起你折腾。能不能再考虑考虑？",
    ],
    "supportive": [
        "你自己决定吧，爸妈相信你。但你真的想清楚了吗？" "能跟爸妈讲讲你为什么这么选吗？",
        "我们不是反对，就是担心。你说的这些，" "你有没有具体的计划？讲给我们听听。",
        "行，既然你想好了，我们就支持你。但你要记住，" "遇到困难别一个人扛，随时跟家里说。",
        "你能把数据摆出来，说明你认真想过。爸妈尊重你的选择，"
        "但你得对得起自己的决定，别半途而废。",
    ],
}


def practice_reply(db: Session, session_id, user_id, message: str) -> dict:
    """模拟父母视角回复用户的话。

    - 若配置了 LLM_API_KEY，用 AI 生成更贴合上下文的父母回复。
    - 否则用预设回复模板（按父母类型轮换）。
    - 将用户消息 + 父母回复追加到 practice_messages，并更新状态。

    返回 parent role 的 message dict：{"role": "parent", "content": "..."}
    """
    session = get_session(db, session_id, user_id)
    if session is None:
        raise ValueError("会话不存在或无权访问")

    # 追加用户消息
    messages = list(session.practice_messages or [])
    messages.append({"role": "user", "content": message})

    # 生成父母回复
    reply: str
    if settings.LLM_API_KEY:
        try:
            reply = _practice_reply_via_llm(session, message, messages)
            if not reply:
                reply = _next_template_reply(session)
        except Exception as e:
            logger.warning("LLM 模拟父母回复失败，回退到模板: %s", e)
            reply = _next_template_reply(session)
    else:
        reply = _next_template_reply(session)

    messages.append({"role": "parent", "content": reply})

    session.practice_messages = messages
    if session.status == "preparing":
        session.status = "practiced"
    db.commit()
    db.refresh(session)

    return {"role": "parent", "content": reply}


def _next_template_reply(session: FamilyDialogueSession) -> str:
    """从预设模板中轮换取下一条父母回复。"""
    archetype = session.parent_archetype or "stability_first"
    replies = _PRACTICE_REPLIES.get(archetype, _PRACTICE_REPLIES["stability_first"])
    # 根据已有 parent 消息数量轮换
    parent_count = sum(1 for m in (session.practice_messages or []) if m.get("role") == "parent")
    return replies[parent_count % len(replies)]


def _practice_reply_via_llm(
    session: FamilyDialogueSession, message: str, messages: list[dict]
) -> str:
    """用 LLM 生成父母视角回复（同步包装，内部调用 async）。

    注意：本函数为同步接口，内部 LLM 调用通过 asyncio.run 执行。
    为避免在已有事件循环的场景下报错，调用方应优先走 async 版本。
    """
    # 此处保留同步实现供 practice_reply 直接调用；
    # 真正的 LLM 调用放在 _practice_reply_via_llm_async，由上层按需 await。
    return _practice_reply_via_llm_sync(session, message, messages)


def _practice_reply_via_llm_sync(
    session: FamilyDialogueSession, message: str, messages: list[dict]
) -> str:
    """同步执行 LLM 父母视角回复（内部用 asyncio.run）。"""
    import asyncio

    try:
        return asyncio.run(_practice_reply_via_llm_async(session, message, messages))
    except RuntimeError:
        # 已有事件循环时，退化为模板
        return ""


async def _practice_reply_via_llm_async(
    session: FamilyDialogueSession, message: str, messages: list[dict]
) -> str:
    """用 LLM 生成父母视角回复。"""
    from app.services.ai_orchestrator import AIOrchestrator

    archetype = session.parent_archetype or "stability_first"
    archetype_label = PARENT_ARCHETYPE_LABELS.get(archetype, archetype)
    saying = PARENT_ARCHETYPE_SAYINGS.get(archetype, "")

    # 构建对话历史摘要（最近 6 条）
    recent = messages[-6:]
    history = "\n".join(
        f"{'用户' if m['role'] == 'user' else '父母'}：{m['content']}" for m in recent
    )

    system_prompt = (
        f"你扮演一位{archetype_label}的中国大学生父母，核心信念是「{saying}」。"
        "你正在和孩子讨论 ta 的职业选择。你的语气要真实——"
        "有担忧、有唠叨、有爱，偶尔固执，但听得进道理。"
        "每次回复 1-3 句话，像真实父母说话，不要说教，不要列要点。"
        "如果孩子说动你了，可以松动一点；如果孩子态度不好，你会更固执。"
    )
    user_prompt = (
        f"【父母担忧】{session.parent_concern}\n"
        f"【孩子选择】{session.user_choice}\n"
        f"【近期对话】\n{history}\n\n"
        f"请以父母身份回复孩子刚才说的话。"
    )
    orchestrator = AIOrchestrator()
    return await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_prompt, timeout=30)


# ----------------------------------------------------------------------
# 查询辅助
# ----------------------------------------------------------------------
def get_session(db: Session, session_id, user_id) -> FamilyDialogueSession | None:
    """获取单条会话（校验归属）。"""
    from uuid import UUID

    try:
        sid = UUID(str(session_id)) if not isinstance(session_id, UUID) else session_id
    except ValueError:
        return None
    return (
        db.query(FamilyDialogueSession)
        .filter(
            FamilyDialogueSession.id == sid,
            FamilyDialogueSession.user_id == user_id,
        )
        .first()
    )


def list_sessions(db: Session, user_id) -> list[FamilyDialogueSession]:
    """获取用户的历史会话（按时间倒序）。"""
    return (
        db.query(FamilyDialogueSession)
        .filter(FamilyDialogueSession.user_id == user_id)
        .order_by(FamilyDialogueSession.created_at.desc())
        .all()
    )


def complete_session(db: Session, session_id, user_id) -> FamilyDialogueSession | None:
    """标记会话为已完成。"""
    session = get_session(db, session_id, user_id)
    if session is None:
        return None
    session.status = "completed"
    db.commit()
    db.refresh(session)
    return session
