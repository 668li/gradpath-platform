# backend/app/services/career_test_drive_service.py
"""职业试驾服务层 — 生成第一人称一日体验。

- ``generate_experience``: 根据路径类型与目标角色生成一日体验。
  优先用 LLM 生成（需配置 ``LLM_API_KEY``）；未配置或调用失败时回退到预设模板，
  保证离线/测试环境始终返回有效内容。
- 模板覆盖 6 种常见路径：考研-计算机 / 考研-文科 / 就业-互联网产品经理 /
  就业-软件开发 / 考公-基层 / 考公-机关。
- 每个模板包含 8-10 个时间段（08:00-22:00），含真实的时间、活动、描述与情绪起伏。
"""
import json
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_test_drive import CareerTestDrive

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 预设模板：6 种常见路径的一日体验
# 每个模板 = {target_role, summary, pros, cons, time_blocks}
# ─────────────────────────────────────────────

_TEMPLATES: list[dict] = [
    # 1. 考研-计算机
    {
        "path_type": "kaoyan",
        "target_role": "考研计算机",
        "summary": (
            "实验室里的一天：从早到晚被代码、论文和组会填满。科研的兴奋与卡 bug 的焦虑交替，"
            "晚上还要继续跑实验。这是苦行僧式的生活，但每一次跑通模型都让你觉得值。"
        ),
        "pros": [
            "前沿技术触达：能接触最前沿的算法与算力",
            "学术成果可累积：论文是可量化的资产",
            "导师人脉与实验室资源加持求职",
        ],
        "cons": [
            "时间被实验绑架，工作生活边界模糊",
            "论文反复被拒，自我怀疑常伴",
            "2 年机会成本，需面对学历贬值与年龄焦虑",
        ],
        "time_blocks": [
            {"time": "08:30", "activity": "实验室晨更", "description": "到实验室开机，检查昨晚通宵跑的训练任务日志，确认 loss 曲线正常。", "emotion": "专注"},
            {"time": "10:00", "activity": "组会汇报", "description": "向导师汇报上周进展，被追问实验设置的合理性，现场被问到哑口无言。", "emotion": "紧张"},
            {"time": "12:00", "activity": "食堂 + 趴桌午休", "description": "和同门边吃饭边吐槽导师，午饭后在工位趴二十分钟回血。", "emotion": "放松"},
            {"time": "14:00", "activity": "调代码", "description": "复现一篇顶会论文的模型，CUDA 报错排查了两个小时，最后发现是数据预处理问题。", "emotion": "焦虑"},
            {"time": "16:30", "activity": "读文献", "description": "精读两篇 arXiv 新文，在笔记本上记下可借鉴的思路，准备写进 related work。", "emotion": "兴奋"},
            {"time": "19:00", "activity": "晚饭 + 散步", "description": "和室友去校门口吃黄焖鸡，绕操场走两圈聊聊毕业去向。", "emotion": "平静"},
            {"time": "20:30", "activity": "写论文", "description": "对着 LaTeX 改 method 章节，反复斟酌措辞，进度缓慢但必须推进。", "emotion": "疲惫"},
            {"time": "22:00", "activity": "提交夜间训练任务", "description": "重新配置超参，挂上 4 卡训练任务后关灯回宿舍，路上还在想实验设计。", "emotion": "期待"},
        ],
    },
    # 2. 考研-文科
    {
        "path_type": "kaoyan",
        "target_role": "考研文科",
        "summary": (
            "图书馆里的一天：被文献、笔记和写作填满。文科考研的孤独在于没有跑通的代码作为反馈，"
            "只有不断打磨的论证。从晨读到夜自习，是与思想反复博弈的一天。"
        ),
        "pros": [
            "思维深度训练：能锤炼批判性思考与表达",
            "时间自主：研究节奏由自己掌控",
            "未来可向高校、出版、智库等多方向发展",
        ],
        "cons": [
            "缺乏即时反馈，容易陷入自我怀疑",
            "就业面相对窄，需主动拓展技能",
            "学术圈竞争激烈，「非升即走」压力大",
        ],
        "time_blocks": [
            {"time": "08:00", "activity": "图书馆晨读", "description": "占座后开始背诵英语作文模板与专业术语，走廊里全是同样在背书的同学。", "emotion": "困倦"},
            {"time": "10:00", "activity": "精读文献", "description": "读一篇核心期刊论文，用三种颜色的笔做批注：观点/论据/可质疑处。", "emotion": "专注"},
            {"time": "12:30", "activity": "午饭 + 小憩", "description": "食堂随便吃点，回图书馆趴一会，旁边同学的翻书声成了白噪音。", "emotion": "放松"},
            {"time": "14:00", "activity": "整理读书笔记", "description": "把上午的批注誊抄进笔记本，按主题归类，搭建自己的知识图谱。", "emotion": "踏实"},
            {"time": "16:00", "activity": "写作训练", "description": "限时写一篇论述题，写完对照范文自评，发现论证链条还是有漏洞。", "emotion": "受挫"},
            {"time": "18:30", "activity": "晚饭 + 散步", "description": "绕校园走一圈，听一集播客换换脑子。", "emotion": "平静"},
            {"time": "20:00", "activity": "政治/英语刷题", "description": "刷两套真题的选择题，错了的回看知识点，机械但必须坚持。", "emotion": "麻木"},
            {"time": "22:00", "activity": "夜自习收尾", "description": "图书馆闭馆音乐响起，收拾书包回宿舍，路上还在默念今天背过的概念。", "emotion": "充实"},
        ],
    },
    # 3. 就业-互联网产品经理
    {
        "path_type": "employment",
        "target_role": "互联网产品经理",
        "summary": (
            "产品经理的一天被会议切碎：需求评审、用户访谈、数据对齐，真正写文档的时间要靠挤。"
            "推动一件事落地要协调五六个团队，成就感与无力感并存。"
        ),
        "pros": [
            "贴近用户与业务，能看见自己做的功能上线",
            "横向视野广，能快速理解多个领域",
            "职业天花板较高，可向业务负责人发展",
        ],
        "cons": [
            "会议密集，深度工作时间被切碎",
            "需在技术、设计、业务间反复拉扯，心力消耗大",
            "KPI 与功能上线节奏压力，加班成常态",
        ],
        "time_blocks": [
            {"time": "09:30", "activity": "看数据晨会", "description": "到工位先打开数据看板，昨日 DAU 与转化率波动，准备好被 leader 追问的原因。", "emotion": "紧张"},
            {"time": "10:30", "activity": "需求评审", "description": "主持新功能评审会，研发当场质疑方案可行性，反复修改交互细节。", "emotion": "高压"},
            {"time": "12:00", "activity": "工位外卖", "description": "边吃外卖边回钉钉消息，中午也没真正离开工位。", "emotion": "疲惫"},
            {"time": "14:00", "activity": "用户访谈", "description": "和 3 位真实用户视频访谈，听到吐槽自己设计的功能，心情复杂但有用。", "emotion": "兴奋"},
            {"time": "16:00", "activity": "写 PRD", "description": "戴上耳机挤时间写需求文档，被打断 4 次，最终写完一半。", "emotion": "无奈"},
            {"time": "18:30", "activity": "跨部门对齐", "description": "和设计、测试、运营同步下个迭代排期，扯皮两小时才勉强达成一致。", "emotion": "焦躁"},
            {"time": "20:00", "activity": "晚饭 + 复盘", "description": "公司食堂吃完饭回工位，整理今天的访谈纪要，列出明天要推进的卡点。", "emotion": "踏实"},
            {"time": "22:00", "activity": "下班", "description": "打车回家，路上还在群里回复研发的问题，到家已快十一点。", "emotion": "疲惫"},
        ],
    },
    # 4. 就业-软件开发
    {
        "path_type": "employment",
        "target_role": "软件开发",
        "summary": (
            "开发的一天以代码为轴：早会、编码、code review、修 bug。沉浸在心流时时间飞逝，"
            "但联调与 oncall 又把节奏打乱。这是创造与被中断反复拉扯的一天。"
        ),
        "pros": [
            "技术可累积，作品与代码即简历",
            "心流体验强，沉浸编码很有成就感",
            "薪资增长曲线清晰，市场对优秀工程师需求稳定",
        ],
        "cons": [
            "需求频繁变更，返工损耗大",
            "oncall 与线上故障带来隐性压力",
            "技术迭代快，需持续学习避免被淘汰",
        ],
        "time_blocks": [
            {"time": "09:30", "activity": "每日站会", "description": "15 分钟站会同步进度，被 leader 点名问昨天卡住的那个 bug 解决没有。", "emotion": "紧张"},
            {"time": "10:00", "activity": "深度编码", "description": "戴上降噪耳机进入心流，重构一个核心模块，两小时写了 300 行干净的代码。", "emotion": "专注"},
            {"time": "12:00", "activity": "午饭 + 休息", "description": "和同事去园区食堂，聊两嘴技术八卦，回来趴一会。", "emotion": "放松"},
            {"time": "14:00", "activity": "code review", "description": "review 同事的 PR，提了 6 条建议，其中一条架构层面的引发了讨论。", "emotion": "投入"},
            {"time": "16:00", "activity": "联调 + 修 bug", "description": "和前端联调接口，发现是自己的字段命名不一致，返工修了一下午。", "emotion": "烦躁"},
            {"time": "18:30", "activity": "晚饭", "description": "公司食堂吃完，回工位看看监控大盘，一切正常松了口气。", "emotion": "平静"},
            {"time": "20:00", "activity": "学习新技术", "description": "看一小时新框架的官方文档，做笔记，为下个项目做技术储备。", "emotion": "充实"},
            {"time": "21:30", "activity": "下班", "description": "提交今天的代码 push 到远端，关电脑回家，路上听一集技术播客。", "emotion": "满足"},
        ],
    },
    # 5. 考公-基层
    {
        "path_type": "civil_service",
        "target_role": "考公基层",
        "summary": (
            "基层公务员的一天被材料和群众填满：写材料、开会、接待、跑现场。"
            "稳定感与琐碎感交织，但每一次帮群众解决问题都有一点微小的意义感。"
        ),
        "pros": [
            "工作稳定，编制带来长期安全感",
            "贴近基层，能真切影响具体的人",
            "福利保障完善，社会认同度高",
        ],
        "cons": [
            "事务琐碎繁杂，重复性高",
            "晋升论资排辈，天花板可见",
            "突发事件多，节假日值守是常态",
        ],
        "time_blocks": [
            {"time": "08:30", "activity": "签到 + 收发文", "description": "到办公室签到，处理 overnight 的 OA 公文，标记需要今天跟进的几件。", "emotion": "平静"},
            {"time": "10:00", "activity": "材料撰写", "description": "为下周的工作汇报写材料，反复修改措辞，领导要求「再拔高一点高度」。", "emotion": "枯燥"},
            {"time": "11:30", "activity": "群众接待", "description": "接待两位来办事的群众，耐心解释政策，帮一位老人填完表格。", "emotion": "耐心"},
            {"time": "12:00", "activity": "食堂午饭", "description": "和同事在机关食堂吃饭，聊聊最近的考核指标，饭后回办公室休息。", "emotion": "放松"},
            {"time": "14:00", "activity": "下午例会", "description": "参加科室例会，部署本月重点任务，被分到一个不太想干的专项。", "emotion": "无奈"},
            {"time": "16:00", "activity": "下社区", "description": "和同事一起下社区走访，登记台账，鞋上沾满泥巴但心里踏实。", "emotion": "踏实"},
            {"time": "18:00", "activity": "整理台账", "description": "回办公室整理今天走访的台账资料，录入系统，确保数据准确。", "emotion": "机械"},
            {"time": "20:00", "activity": "加班收尾", "description": "把明天要交的材料再过一遍，领导签字后才下班回家。", "emotion": "疲惫"},
        ],
    },
    # 6. 考公-机关
    {
        "path_type": "civil_service",
        "target_role": "考公机关",
        "summary": (
            "机关公务员的一天以公文、调研、汇报为轴：处理来文、起草文稿、参加调研座谈。"
            "节奏比基层慢，但材料要求更高，是在文字与流程间精雕细琢的一天。"
        ),
        "pros": [
            "平台层级高，能接触宏观政策制定",
            "工作节奏相对可控，加班少于基层",
            "晋升通道更清晰，发展空间更大",
        ],
        "cons": [
            "材料要求高，反复打磨耗心力",
            "层级森严，决策权有限",
            "工作成果不易被外界看见，价值感需自我寻找",
        ],
        "time_blocks": [
            {"time": "09:00", "activity": "处理来文", "description": "登录 OA 处理昨日积压来文，分门别类拟办意见，重要件标注呈送领导。", "emotion": "专注"},
            {"time": "10:30", "activity": "起草文稿", "description": "起草一份调研报告提纲，反复斟酌小标题的对仗与逻辑层次。", "emotion": "投入"},
            {"time": "12:00", "activity": "食堂午饭", "description": "和处室同事在食堂就餐，聊两句家常，饭后散步消食。", "emotion": "放松"},
            {"time": "14:00", "activity": "调研座谈", "description": "随领导参加一场专题调研座谈会，认真记录发言要点，会后整理纪要。", "emotion": "认真"},
            {"time": "16:00", "activity": "汇报沟通", "description": "向处长汇报报告初稿，被指出几处表述需调整，回去继续打磨。", "emotion": "紧张"},
            {"time": "18:00", "activity": "学习文件", "description": "学习最新下发的政策文件，圈画重点，为后续撰写材料积累素材。", "emotion": "平静"},
            {"time": "19:30", "activity": "下班", "description": "整理桌面与明日待办，准点下班，难得按时回家。", "emotion": "满足"},
            {"time": "21:00", "activity": "自我提升", "description": "在家看一小时申论与公文写作网课，为遴选考试做准备。", "emotion": "充实"},
        ],
    },
]


def _normalize(role: str) -> str:
    return (role or "").strip().lower()


def _find_template(path_type: str, target_role: str) -> dict:
    """根据路径类型与目标角色匹配最贴近的模板。

    匹配优先级：target_role 完全包含关键词 → path_type 相同 → 第一个模板兜底。
    """
    role = _normalize(target_role)
    ptype = _normalize(path_type)
    # 1) 关键词匹配
    keyword_map = [
        ("计算机", "考研计算机"), ("理工", "考研计算机"), ("算法", "考研计算机"),
        ("文科", "考研文科"), ("语言", "考研文科"), ("历史", "考研文科"), ("哲学", "考研文科"),
        ("产品", "互联网产品经理"), ("pm", "互联网产品经理"),
        ("开发", "软件开发"), ("程序", "软件开发"), ("软件", "软件开发"), ("后端", "软件开发"), ("前端", "软件开发"),
        ("基层", "考公基层"), ("乡镇", "考公基层"), ("街道", "考公基层"),
        ("机关", "考公机关"), ("部委", "考公机关"), ("省直", "考公机关"), ("市直", "考公机关"),
    ]
    for kw, tmpl_role in keyword_map:
        if kw in role:
            for t in _TEMPLATES:
                if t["target_role"] == tmpl_role:
                    return t
    # 2) path_type 相同取第一个
    for t in _TEMPLATES:
        if _normalize(t["path_type"]) == ptype:
            return t
    # 3) 兜底
    return _TEMPLATES[0]


def _from_template(path_type: str, target_role: str) -> dict:
    """从模板生成一日体验（深拷贝，避免污染模板）。"""
    tmpl = _find_template(path_type, target_role)
    # 模板用原始 target_role 展示，但保留用户输入角色名（更贴合用户选择）
    return {
        "target_role": target_role or tmpl["target_role"],
        "path_type": path_type or tmpl["path_type"],
        "time_blocks": [dict(b) for b in tmpl["time_blocks"]],
        "summary": tmpl["summary"],
        "pros": list(tmpl["pros"]),
        "cons": list(tmpl["cons"]),
    }


async def _from_llm(path_type: str, target_role: str, user_context: dict | None) -> dict | None:
    """调用 LLM 生成一日体验。失败返回 None，由调用方回退到模板。"""
    from app.services.ai_orchestrator import AIOrchestrator
    from app.services.ai_service import AIServiceNotConfigured

    system_prompt = (
        "你是职业体验师，擅长以第一人称视角描绘某条职业路径一天的沉浸式体验。"
        "请输出严格 JSON，字段：time_blocks(8-10 个，每个含 time/activity/description/emotion，"
        "时间从早到晚覆盖 08:00-22:00)、summary(一日总结,80-150字)、pros(3条优点)、cons(3条挑战)。"
        "活动要具体真实，情绪要有起伏（专注/紧张/兴奋/疲惫等），不要输出 JSON 以外的内容。"
    )
    ctx_line = f"\n用户背景：{user_context}" if user_context else ""
    user_content = (
        f"请为以下路径生成第一人称一日工作体验：\n"
        f"路径类型：{path_type}\n目标角色：{target_role}{ctx_line}"
    )
    try:
        orchestrator = AIOrchestrator()
        raw = await orchestrator.chat(system_prompt, user_content, timeout=30)
        # 揼出 JSON（LLM 偶尔会包裹 ```json ... ```）
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        # 基本校验
        blocks = data.get("time_blocks") or []
        if not isinstance(blocks, list) or len(blocks) < 6:
            logger.warning("LLM 返回 time_blocks 不足，回退模板: %s", raw[:200])
            return None
        normalized_blocks = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            normalized_blocks.append({
                "time": str(b.get("time", "")),
                "activity": str(b.get("activity", "")),
                "description": str(b.get("description", "")),
                "emotion": str(b.get("emotion", "")),
            })
        if len(normalized_blocks) < 6:
            return None
        return {
            "target_role": target_role,
            "path_type": path_type,
            "time_blocks": normalized_blocks,
            "summary": str(data.get("summary", "")),
            "pros": [str(p) for p in (data.get("pros") or [])][:5],
            "cons": [str(c) for c in (data.get("cons") or [])][:5],
        }
    except AIServiceNotConfigured:
        # 未配置 LLM：orchestrator 内部直接抛出，不重试 → 回退模板（降级语义保持）
        logger.info("LLM 未配置，使用模板生成")
        return None
    except Exception as e:
        logger.warning("LLM 生成失败，回退模板: %s", e)
        return None


async def generate_experience(
    path_type: str,
    target_role: str,
    user_context: dict | None = None,
) -> dict:
    """生成一日体验内容。

    优先用 LLM；未配置或失败时回退到预设模板，保证始终返回有效内容。
    返回 dict: {target_role, path_type, time_blocks, summary, pros, cons}
    """
    result = await _from_llm(path_type, target_role, user_context)
    if result is None:
        result = _from_template(path_type, target_role)
    return result


# ─────────────────────────────────────────────
# 持久化 CRUD
# ─────────────────────────────────────────────


async def create_drive(db: Session, user_id: UUID, path_type: str, target_role: str) -> CareerTestDrive:
    """生成并持久化一条试驾记录。"""
    content = await generate_experience(path_type, target_role)
    drive = CareerTestDrive(
        user_id=user_id,
        path_type=content["path_type"],
        target_role=content["target_role"],
        experience_content=content,
    )
    db.add(drive)
    db.commit()
    db.refresh(drive)
    return drive


def list_drives(db: Session, user_id: UUID) -> list[CareerTestDrive]:
    return (
        db.query(CareerTestDrive)
        .filter(CareerTestDrive.user_id == user_id)
        .order_by(CareerTestDrive.created_at.desc())
        .all()
    )


def get_drive(db: Session, user_id: UUID, drive_id: UUID) -> CareerTestDrive | None:
    return (
        db.query(CareerTestDrive)
        .filter(CareerTestDrive.id == drive_id, CareerTestDrive.user_id == user_id)
        .first()
    )
