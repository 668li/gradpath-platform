"""门道卡 seed 数据 — 2026-09-26 批次 B+ 生产导入的唯一真相源。

来源：两路 AI 定向检索+交叉验证（A 组 14 卡 / C+D 组 11 卡），全部来源链
经 HTTP 实测可打开（87/88，1 条 404 死链已剔除——D2 卡第 4 源）。
置信度口径：来源链含官方域名（.gov.cn/.edu.cn/chsi.com.cn/.cnr.cn 国家媒体）
直证才标 official；仅媒体转述一律 multi_source；无孤证卡（单源不收卡）。
卡片只存提炼结论与来源链，不搬运原文（CONTEXT.md 门道卡纪律）。
维护协议见 docs/门道卡-维护协议-2026-09-26.md：招生政策年变，as_of 过期复审。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.intel_card import IntelCard

logger = logging.getLogger(__name__)

_AS_OF = "2026-09"
_TRACK = "kaoyan"

_QUESTION_TEXT = {
    "A1": "复试前要不要提前联系导师？什么时机联系最合适？",
    "A2": "联系导师的邮件怎么写才容易得到回复？",
    "A3": "复试现场有哪些「流程图上没有」的实际门道？",
    "A4": "调剂系统里有哪些潜规则？",
    "A5": "择校时哪些「官方数据看不出」的坑要避开？",
    "A6": "报考点选择有什么门道？",
    "A7": "复试着装/线上机位有什么讲究？",
    "A8": "怎么提前判断导师人品与组风？",
    "A9": "推免/夏令营是怎么挤占统考名额的？",
    "C1": "怎么提前看出目标院校今年会不会扩招/缩招？",
    "C2": "专业课改考科目/换参考书有什么预警信号？",
    "C3": "某导师今年招不招人怎么提前知道？",
    "C4": "专业课「水区旱区」（阅卷宽严差）真实存在吗？",
    "C5": "官方不公布的真题去哪里找？",
    "C6": "复试英语口语一般问什么？",
    "D1": "专业课「压分」是真实存在的吗？怎么实锤判定？",
    "D2": "复试歧视双非是真的吗？",
    "D3": "「一志愿保护」是真是假？",
    "D4": "复试刷人有多狠？（差额比实锤）",
    "D5": "拟录取名单里能读出哪些隐藏信息？",
}

_CARDS: list[dict] = [
    # ---------------- A 组·门道潜规则 ----------------
    {
        "question_id": "A1",
        "category": "rule",
        "title": "联系导师：出分后是黄金窗口",
        "conclusion": (
            "要联系，但别盲联。初试成绩公布后尽早（约3-7天内）带着分数和排名发邮件最有效；"
            "复试线公布后再联系适合擦线生确认资格；复试前一周可再告知行程争取见面；"
            "院校明令禁止考前联系或实行双盲复试的，不要联系。"
        ),
        "conditions": (
            "适用于统考考生且院校未禁止提前联系；自身分数有基本竞争力、对目标导师方向做过功课；"
            "排名靠后时导师回复率很低，联系意义有限。"
        ),
        "counterexample": (
            "部分院校（如云南大学）明确规定复试前不用联系导师或采用双盲复试；"
            "文科理论型专业导师更看重复试现场表现，提前联系作用有限。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "掌上考研：联系导师是门技术活——这4个时机+3个模板", "url": "https://m.kaoyan.cn/article/214875", "supports": "出成绩后/复试线公布后/复试结束后三时机与院校禁联情形"},
            {"title": "启航考研：考研复试联系导师方法及注意事项", "url": "https://jixun.iqihang.com/zixun/fushi/fszd/20188227.html", "supports": "出分后是统考生联系黄金期、复试前一周告知行程"},
            {"title": "考研招生网：考研成绩出来后要联系导师吗", "url": "https://m.kyzs.com/article/18083.html", "supports": "排名一般时导师回复可能性低"},
        ],
    },
    {
        "question_id": "A2",
        "category": "rule",
        "title": "导师邮件：主题+匹配度定回复率",
        "conclusion": (
            "高回复率邮件=规范主题+精炼正文+针对性内容。主题写「姓名-报考专业-初试总分-自荐」；"
            "正文300字左右：分数与排名、读过导师论文后的具体兴趣点、个人亮点（科研/竞赛/毕业论文）、表态致谢，"
            "附1页简历。工作日上午发送，发件人改真名，不勾已读回执。"
        ),
        "conditions": (
            "有具体亮点和针对性内容时成立；对同一学院多位导师不可群发同一模板，"
            "应按优先级依次投递，一位导师约一周未回复可补发一次后换人。"
        ),
        "counterexample": (
            "导师姓名、职称、研究方向写错会直接出局；群发同一模板被识别为广撒网，"
            "会留下不真诚印象并影响复试评分。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "无忧考网：考研复试联系导师邮件模板，回复率高的写法", "url": "https://wuyou360.cn/kypx/1167.html", "supports": "标题公式、300字四段结构、群发是复试大忌"},
            {"title": "彩虹网：考研出分必看！联系导师全攻略", "url": "https://www.jscaihong.com/cai/45486.html", "supports": "邮件主题规范格式与正文结构"},
            {"title": "研发家：考研出分后真心建议大家这样联系导师", "url": "https://www.yanfajia.com/news/6912.html", "supports": "不勾已读回执、7天未回复二次联系后换导师"},
            {"title": "长沙海文考研：复试提前联系导师？模板来了", "url": "https://www.jiaoyubao.cn/news/n303407.html", "supports": "一封一投、引用导师论文具体观点比空泛崇拜有效"},
        ],
    },
    {
        "question_id": "A3",
        "category": "rule",
        "title": "差额复试：高分不等于保险",
        "conclusion": (
            "复试普遍为差额制，常见比例1:1.2~1:1.5，热门专业更高；复试占总成绩比例一般在30%-50%。"
            "复试权重越高，初试分差越易被抹平——复试占50%时，复试多拿几分就能抹平初试十几分的差距。"
            "每年都有初试高分甚至第一名被刷、压线逆袭的案例，拿到拟录取前不能松懈。"
        ),
        "conditions": (
            "适用于实行差额复试的院校（绝大多数）；复试占比高、招生名额少或差额比大的专业风险最大，"
            "报考时就应关注复试权重。"
        ),
        "counterexample": "等额复试、或初试占比70%且分差悬殊时，初试高分被翻盘的概率明显降低。",
        "confidence": "multi_source",
        "sources": [
            {"title": "中国农业大学2026年硕士研究生招生简章（新东方在线转载）", "url": "https://kaoyan.koolearn.com/20250923/1877826.html", "supports": "简章载明复试差额比例一般不低于120%、复试占总成绩30%-50%"},
            {"title": "国际教育联盟：考研复试被翻盘的概率有多大", "url": "https://www.jingsailian.com/news/1555586.html", "supports": "差额比对应16%-33%淘汰率与逆袭分差折算"},
            {"title": "研线网：2021考研复试为啥高分复试被刷", "url": "http://www.yanxian.org/html/fsjy/37063.html", "supports": "部分专业1:3差额与高分被刷常见硬伤"},
            {"title": "今日头条：复试特别注意，高分也可能被淘汰", "url": "https://www.toutiao.com/article/7462723101492347429/", "supports": "复试占比30%-70%不等、权重越高初试影响越小"},
        ],
    },
    {
        "question_id": "A3",
        "category": "rule",
        "title": "复试现场：坦诚与保密红线",
        "conclusion": (
            "不会的问题坦诚承认并尝试从相关角度分析，不懂装懂被追问是最大扣分点；"
            "被质疑时先认可再讲反思，与老师争辩、固执己见是硬伤；「导师让我做的」这类被动回答暴露无思考。"
            "复试内容保密：复试后在群里讨论真题、录音录屏泄题可被取消成绩乃至取消录取资格。"
        ),
        "conditions": (
            "适用于线上线下面试的应答环节与复试全程；评委多为中老年教师，"
            "谦虚诚恳、展示思路比完美答案更受青睐。"
        ),
        "counterexample": (
            "只说「不知道」不展开同样扣分——承认后给出相关思路和改进意愿才是得分姿态；"
            "完全沉默或傻站着最差。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "今日头条：考研复试评委自白——9小时21个考生后的真心话", "url": "https://www.toutiao.com/article/7620686766118404642/", "supports": "不会别强行找补、不要反驳老师、诚实考生逆袭案例"},
            {"title": "查字典考研网：现场实录——考生导师口述考研复试得失经验", "url": "https://kaoyan.chazidian.com/kaoyan/386745/", "supports": "不懂装懂、与导师争辩、手机铃响致失败的现场案例"},
            {"title": "考研论坛：初试400+，复试还是被刷了", "url": "http://bbs.kaoyan.com/t10436665p1", "supports": "人大法硕考生复试后群内讨论真题被记0分事件"},
            {"title": "浙江理工大学2025年网络远程复试指南（中国考研网转载）", "url": "https://www.chinakaoyan.com/info/article/id/602351.shtml", "supports": "官方考场规则：录音录屏泄题取消复试成绩"},
        ],
    },
    {
        "question_id": "A4",
        "category": "rule",
        "title": "调剂：开系统前胜负已定半",
        "conclusion": (
            "调剂的真正竞争在正式系统开通前：招生单位会提前发布缺额预告、通过调剂意向采集系统"
            "（最多10个意向）和自主预调剂收集考生信息，很多院校在预调剂阶段就锁定了复试人选，"
            "提前联系研招办和导师的考生优先获得机会；等正式系统开了再找，优质缺额往往已被占。"
        ),
        "conditions": (
            "适用于擦线一志愿或复试可能被刷的考生，国家线公布后即应启动信息收集；"
            "所有调剂手续最终仍必须通过研招网调剂服务系统完成，系统外调剂无效。"
        ),
        "counterexample": (
            "也有院校严格按系统填报顺序和调剂条件筛选，提前联系只是获取信息的渠道，"
            "并不构成任何录取承诺。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "网易：2026考研调剂攻略——流程、时间、要点全覆盖", "url": "https://www.163.com/dy/article/KOSLGSDR0552IZCQ.html", "supports": "意向采集10个意向转3个志愿机制、预调剂优先安排复试"},
            {"title": "橙啦：考研调剂是怎么调剂的？全流程+捡漏技巧", "url": "https://eva.orangevip.com/detail/732", "supports": "很多学校预调剂阶段就招满、正式系统反而没名额"},
            {"title": "新东方前途出国：考研调剂不踩坑2026最新实操指南", "url": "https://liuxue.xdf.cn/blog/blog_7871810.shtml", "supports": "院校提前发布缺额预告、优先接收提前咨询的考生"},
            {"title": "沃顿教育：2026考研预调剂系统已开放", "url": "https://www.jiaoyubao.cn/news/n339261.html", "supports": "意向采集系统先于正式系统开通、最多10个平行意向"},
        ],
    },
    {
        "question_id": "A4",
        "category": "rule",
        "title": "调剂三志愿：锁定36小时的博弈",
        "conclusion": (
            "调剂系统一次最多填3个平行志愿，提交即被锁定，时长由招生单位自设（最长不超过36小时），"
            "每志愿单独计时，锁定期内不能修改。不要一次填满3个，留1个机动应对新缺额；"
            "到期未获处理可致电研招办请求解锁；接受「待录取」即调剂完成，不能再接受其他院校。"
        ),
        "conditions": (
            "适用于调剂系统操作期；填报前务必核对院校调剂条件，"
            "警惕「锁王」院校（不拒绝也不解锁、白等36小时）和复试时间冲突的院校。"
        ),
        "counterexample": (
            "有的院校明确不接受提前解锁申请，打电话也没用；"
            "个别院校调剂实为校内调剂优先，外校填报会被挂到自动解锁。"
        ),
        "confidence": "official",
        "sources": [
            {"title": "央广网：2026考研调剂系统开通速看操作指南", "url": "https://news.cnr.cn/native/gd/kx/20260408/t20260408_527577318.shtml", "supports": "3个平行志愿、锁定最长不超过36小时、确认待录取即调剂完成"},
            {"title": "学而思考研帮：调剂志愿填报技巧", "url": "https://www.kaoyan.com/adjust/1/9/61df4da50af145db843e1514e6ded0dd?bc=adjust", "supports": "不要一次性填满、提前解锁可致电招生办"},
            {"title": "尚德机构：24考研调剂避坑指南", "url": "https://www.sunlands.com/mba/detail/1214", "supports": "留一个备用志愿、校内调剂优先院校不拒不解"},
            {"title": "研招网复试调剂专题", "url": "https://yz.chsi.com.cn/yztj/", "supports": "官方系统入口：所有调剂须通过研招网调剂服务系统"},
        ],
    },
    {
        "question_id": "A5",
        "category": "rule",
        "title": "择校第一坑：统考实缺≠拟招总数",
        "conclusion": (
            "招生简章的「拟招生人数」是含推免的总盘子，真实统考名额=总计划数-推免拟录取数。"
            "热门专业推免占比超50%很常见，个别接近100%；只看总数会严重高估机会。"
            "择校要查近3年拟录取名单，算出统考实缺及其趋势，统考名额逐年走低的专业慎报。"
        ),
        "conditions": (
            "适用于所有择校场景，尤其名校热门专业与学硕；"
            "推免拟录取名单通常10月中下旬才公示，此前名额均未最终确定。"
        ),
        "counterexample": (
            "部分院校推免招不满，剩余招生计划明确转入统考（如中国农业大学简章载明），"
            "实际统考名额会多于按推免上限的悲观预估。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "MBAChina：27考研择校梯度规划", "url": "https://www.mbachina.com/html/xw/202608/658341.html", "supports": "统考实缺=总数-推免拟录取的计算法、热门专业推免占比50%-60%常态"},
            {"title": "51升学平台：2027考研招生简章陆续发布，择校前重点核查这几项", "url": "https://51hxw.com/kyzx/719.html", "supports": "统考实际名额=总招生-推免拟录取、需核对近3年差异"},
            {"title": "启航考研：27考研择校别只看复试线", "url": "https://jixun.iqihang.com/zixun/changshi/2026803148.html", "supports": "误把推免名额算进统考名额是常见误区"},
            {"title": "中国农业大学2026年硕士研究生招生简章（新东方在线转载）", "url": "https://kaoyan.koolearn.com/20250923/1877826.html", "supports": "官方简章：推免结束后剩余计划转入统考"},
        ],
    },
    {
        "question_id": "A5",
        "category": "rule",
        "title": "官方数据看不出的三个坑",
        "conclusion": (
            "择校要防三类官方口径看不出的坑：一是专业课压分——一志愿上线极少、专业课普遍低分，"
            "直接失去调剂资格；二是不保护一志愿——一志愿与调剂生同卷排名、设「优质生源专项」预留名额；"
            "三是复试或拟录取公示过晚——被刷后错过调剂窗口。核验靠对比近2-3年复试名单与拟录取名单、"
            "看专业课分数分布、多方打听在读生风评。"
        ),
        "conditions": (
            "双非、跨考或初试分不占优的考生风险最大；网传「黑名单」多为个体主观反馈、无官方定性，"
            "同校不同专业差异大，需用数据核实而非贴标签。"
        ),
        "counterexample": (
            "压分对报考同一学校的考生内部是公平的（一起压），只有压到过不了线、无法调剂时才是致命坑；"
            "保护一志愿的院校即使在调剂中也优先一志愿。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "新东方：考研择校潜规则——不保护一志愿的学校再好也别碰", "url": "https://www.xdf.cn/234/202609/15367563.html", "supports": "不保护一志愿的三种典型表现与识别方法"},
            {"title": "新东方：28考研择校避雷指南", "url": "https://mtoutiao.xdf.cn/www/601/202608/15359780.html", "supports": "四类高风险院校特征与黑名单需数据核实的提醒"},
            {"title": "研线网：院校是否保护一志愿怎么看出来", "url": "http://www.yanxian.org/html/kyjj/42396.html", "supports": "三种操作手法与优质调剂生源专项计划"},
            {"title": "MBAChina：考研调剂避雷指南", "url": "https://www.mbachina.com/html/xw/202504/616111.html", "supports": "压分识别、复试过晚与海王锁王特征"},
        ],
    },
    {
        "question_id": "A6",
        "category": "rule",
        "title": "报考点先到先得，热门地区要抢",
        "conclusion": (
            "报考点考位容量有限、报满即止，热门城市考点可能预报名首日就被抢空，"
            "报满只能换其他报考点甚至去外地考试。策略：预报名开启当天尽早提交并缴费；"
            "报满后可蹲守未缴费释放的名额、关注省级增补考点、换周边区县或回户籍地；"
            "报考点不等于考点，选考试院/招办类报考点的考场随机分配。"
        ),
        "conditions": (
            "主要适用于川渝、京津沪等报考热门地区；"
            "网报提交生成报名号后「招生单位、报考点、考试方式」不可修改，提交前须反复核对。"
        ),
        "counterexample": (
            "部分省份官方表态考位总体充足、建议错峰报考（如四川省2026年网报问答称全省近70个报考点整体考位充足），"
            "冷门地区无需恐慌。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "尚研考研：考研预报名，这些火爆报考点手慢真的无", "url": "https://www.shangyanjiaoyu.com/574.html", "supports": "四川首日约半数考点报满、凌晨回流名额、3个梯度备选"},
            {"title": "新东方在线：考研想报的报考点满了怎么办", "url": "https://news.koolearn.com/kaopei/kyzx/43424/", "supports": "刷系统捡漏、换考点、关注新增报考点"},
            {"title": "新东方在线：成都考研报考点满了怎么办还能去哪报", "url": "https://kaoyan.koolearn.com/20260910/1975683.html", "supports": "换区县/周边城市/回户籍地的替代方案"},
            {"title": "四川省教育考试院：2026年考研网上报名相关问题解答", "url": "https://www.sceea.cn/Html/202509/Newsdetail_4464.html", "supports": "官方：生成报名号后关键信息不可修改、考位官方口径"},
        ],
    },
    {
        "question_id": "A6",
        "category": "rule",
        "title": "往届生异地报考：材料是硬门槛",
        "conclusion": (
            "往届生报考点规则为「户籍或工作所在地」：回户籍地只需户口本；"
            "异地报考须提供社保缴费记录或居住证/工作证明，各报考点要求差异大且逐年收紧"
            "（如广州要求当年1-10月社保或居住证，南京要求近3个月社保）。"
            "必须逐字阅读目标报考点网报公告并电话确认，材料不合规审核将不通过。"
        ),
        "conditions": (
            "适用于所有往届生（含二战）选择非户籍地报考点；"
            "社保有时限要求（近3个月连续），居住证办理需15-30天，须提前数月准备。"
        ),
        "counterexample": (
            "应届生规则简单——原则上选就读学校所在地报考点；"
            "但部分高校报考点只接受特定生源或限定专业（如MBA限指定考点），选错不予确认。"
        ),
        "confidence": "official",
        "sources": [
            {"title": "广州市招生办公室2025年考研报考点通告", "url": "https://gzzk.gz.gov.cn/qtks/qtksxx/wjtz/content/post_9902129.html", "supports": "官方：异地报考须社保记录或居住证、报满另选报考点"},
            {"title": "南京市教育招生考试院2025年报考点公告", "url": "https://edu.nanjing.gov.cn/zb/gxzs/202410/t20241031_4997653.html", "supports": "官方：非南京户籍往届生须近三个月社保"},
            {"title": "新东方在线：往届生考研报考点选择指南", "url": "https://kaoyan.koolearn.com/20251009/1878953.html", "supports": "户籍地最稳妥、网报公告是唯一依据"},
            {"title": "四川省教育考试院：2026年考研网上报名相关问题解答", "url": "https://www.sceea.cn/Html/202509/Newsdetail_4464.html", "supports": "官方：在川工作户口未随迁者须在职证明+近三个月社保"},
        ],
    },
    {
        "question_id": "A7",
        "category": "rule",
        "title": "着装整洁即可，线上守双机位",
        "conclusion": (
            "着装：复试不要求正装，整洁大方、有学生气即可，避免拖鞋破洞、浓妆、夸张配饰，"
            "女生淡妆扎发、忌短透紧；线上还忌细条纹和纯白衣物（镜头频闪、融背景）。"
            "机位：主机位（电脑）置于正前方拍头肩双手，辅机位（手机）置于侧后方45°拍屏幕和环境并全程静音，"
            "手机用流量作备用网络，不得美颜滤镜。"
        ),
        "conditions": (
            "适用于无特殊着装要求的多数院校；线上双机位具体要求以报考院校当年复试细则为准，"
            "考前务必参加院校组织的模拟测试。"
        ),
        "counterexample": (
            "法学、管理等严肃专业或个别看重着装的场合可提升正式度；"
            "未按要求摆放机位经提醒不改正、复试中录屏泄题，按违规取消复试成绩。"
        ),
        "confidence": "official",
        "sources": [
            {"title": "中国科学技术大学：考生双机位复试操作说明", "url": "https://yz1.ustc.edu.cn/userfiles/202203/1647414007132572955.pdf", "supports": "官方：辅机位侧后方45°、手机流量双机热备、不得过度修饰仪容"},
            {"title": "浙江理工大学2025年网络远程复试指南（中国考研网转载）", "url": "https://www.chinakaoyan.com/info/article/id/602351.shtml", "supports": "官方规则：不得美颜滤镜、机位不合规提醒不改按违规处理"},
            {"title": "新航道：考研复试穿什么", "url": "https://bj.xhd.cn/kydt/833131.html", "supports": "简约正式、干净得体原则与按专业微调"},
            {"title": "新东方在线：考研网络复试需要注意什么", "url": "https://news.koolearn.com/kaopei/kyzx/189578/", "supports": "条纹衣物上镜频闪、背景整洁"},
        ],
    },
    {
        "question_id": "A8",
        "category": "rule",
        "title": "导师人品：找3个人交叉验证",
        "conclusion": (
            "最可靠的核查路径：联系2-3名在读及已毕业学生（含同院其他组学生）交叉验证，"
            "问具体事实——组会频率、指导频率、通常几年毕业、补助是否按时、能否实习；"
            "辅以毕业论文致谢、延毕与退学转组率。网络评价差评比好评可信（多个独立差评指向同一问题=高危），"
            "但存在刷好评删差评，只能作参考；被问及时支支吾吾本身就是危险信号。"
        ),
        "conditions": (
            "组内学生可能因避嫌不敢直言，需换组外同院学生或多问几人；"
            "判断延毕、发文节奏要结合所在学科的惯例，不能一刀切。"
        ),
        "counterexample": (
            "评价网覆盖不全（顶尖高校导师数据少）、评价两极化，要求严格的导师也可能被差评；"
            "个别差评可能是情绪化失实信息。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "科学网博客：选导师避坑——看导师评价网靠谱吗", "url": "https://blog.sciencenet.cn/blog-3383728-1474845.html", "supports": "差评可信度高于好评、刷好评删差评风险、线下交叉验证"},
            {"title": "后保研：保研选导师攻略", "url": "https://www.houbaoyan.cn/articles/baoyan-mentor-choice", "supports": "联系2-3个学生验证、延毕率超30%是危险信号、提问话术"},
            {"title": "国际教育联盟：如何才能知道一个导师的人品", "url": "https://www.jingsailian.com/news/1578059.html", "supports": "找组外同院学生打听、回复支支吾吾要慎重"},
            {"title": "研飞科研指南：仅从论文评估导师课题组", "url": "https://help.ivysci.com/guide/mentor.html", "supports": "学位论文追踪毕业情况、霸占一作兼通讯等论文雷区"},
        ],
    },
    {
        "question_id": "A9",
        "category": "rule",
        "title": "推免如何挤占统考名额",
        "conclusion": (
            "机制有三：一是夏令营/预推免在正式推免系统前提前考核锁定生源，"
            "优秀营员拿到拟录取资格后经推免服务系统确认；二是招生总计划内推免占比上升、统考席位同比例缩水，"
            "政策上限为全校推免不超招生总量50%，但具体专业可远超甚至100%只收推免；"
            "三是推免资格高校扩容（2025年新增67所至超430所），推免池持续扩大。名校学硕与文科小名额专业震荡最大。"
        ),
        "conditions": (
            "主要影响名校热门专业与学硕；全国总量上推免比例受50%上限约束、整体比例稳定，"
            "所谓「全面缩招」是部分学校部分专业的结构性现象。"
        ),
        "counterexample": (
            "推免招不满的专业，剩余计划转入统考；专硕是扩招主力，"
            "2025年统考专硕计划占比超60%的高校达87.4%，多数专业统考通道依然宽阔。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "中国新闻周刊：考研名额，断崖式缩水？（观察者网转载）", "url": "https://www.guancha.cn/politics/2025_10_30_795104.shtml", "supports": "推免挤压统考、全校50%上限、部分专业100%推免"},
            {"title": "掌上考研：研究生扩招却更难考？多校统考名额暴减50%", "url": "https://m.kaoyan.cn:10443/article/214733", "supports": "扩招名额多流向推免、统考名额被挤压的具体算例"},
            {"title": "科学网：全国推免资格高校大扩围，保研概率会增加多少", "url": "https://news.sciencenet.cn/htmlnews/2025/8/549426.shtm", "supports": "2025年新增67所推免资格高校、全国超430所"},
            {"title": "中国教育在线：颠覆认知！保研的方法竟然多达13种", "url": "https://kaoyan.eol.cn/nnews/202207/t20220718_2238350.shtml", "supports": "夏令营优秀营员即拟录取、九月推免系统才具最终效力"},
        ],
    },
    {
        "question_id": "A9",
        "category": "rule",
        "title": "统考名额是弹性的，别被简章吓退",
        "conclusion": (
            "简章数字只是初始计划：部分院校刻意按低比例申报留调整余地，最终录取常高于简章，"
            "各校普遍注明「最终以实际录取为准」；推免名单10月中下旬才定，此前统考名额未尘埃落定。"
            "报名决策窗口在9月简章发布与10月推免公示之间：核对「总数-推免数」，"
            "统考名额骤减超两成再考虑换专业课相近的备选院校，同时防机构「焦虑营销」放大个案。"
        ),
        "conditions": (
            "适用于9-10月报名决策期；判断缩招要看目标专业自身近3-5年数据和原因"
            "（推免挤压、专业调整还是报考降温），而非只看大盘情绪。"
        ),
        "counterexample": (
            "参考书或考纲特殊的自命题专业，9月后换校几乎等于从头再来，"
            "此时硬换目标不如留在原目标提分。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "中国教育在线：考研真的缩招了？", "url": "https://www.eol.cn/news/guancha/202511/t20251113_2700240.shtml", "supports": "实际录取常高于初始计划、部分缩招恐慌属焦虑营销"},
            {"title": "中国农业大学2026年硕士研究生招生简章（新东方在线转载）", "url": "https://kaoyan.koolearn.com/20250923/1877826.html", "supports": "官方简章：剩余计划和新增计划转入统考"},
            {"title": "新东方在线：2027考研缩招招生简章如何应对名额减少", "url": "https://kaoyan.koolearn.com/20260621/1954326.html", "supports": "缩招20%内属正常波动、备选院校须科目相近"},
            {"title": "MBAChina：27考研推免扩招挤压统考席位，普通考生怎么选", "url": "https://www.mbachina.com/html/xw/202608/658172.html", "supports": "9月信息核对月、核算统考实缺后再调志愿"},
        ],
    },
    # ---------------- C 组·圈内消息 ----------------
    {
        "question_id": "C1",
        "category": "circle",
        "title": "扩缩招提前预判三看",
        "conclusion": (
            "提前预判看三处：一是近三年招生目录中统考名额（总计划减推免）走势，连年下降即缩招信号；"
            "二是每年9月推免拟录取公示的实际推免数，比目录计划数更准，实际推免超额会直接挤占统考名额；"
            "三是该校有无连年扩招惯例及停招、新增专业公告。简章公布前一切数字仅是预估，最终以9月正式简章为准。"
        ),
        "conditions": (
            "适用于每年7-9月招生简章与专业目录集中发布期做择校决策；"
            "统计统考名额时需剔除少干、士兵计划等专项名额。"
        ),
        "counterexample": (
            "简章人数并非定数：有院校某年计划招生60人最终录取468人的极端扩招案例，"
            "也存在临近报名才官宣缩招停招的院校。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "启航考研：考研招生目录研读，推免名额、统考名额怎么看", "url": "https://jixun.iqihang.com/zixun/changshi/2026800673.html", "supports": "统考名额算法、9月推免拟录取公示更准、连看三年"},
            {"title": "MBAChina：25考研，缩招趋势已定?", "url": "https://www.mbachina.com/html/xw/202409/597228.html", "supports": "推免比例上升是缩招主因、新疆大学极端扩招反例"},
            {"title": "峰研教育：27考研择校避坑！5个方法预判院校会不会爆", "url": "https://www.jiaoyubao.cn/news/n349933.html", "supports": "近三年统考名额变化判扩缩趋势"},
        ],
    },
    {
        "question_id": "C2",
        "category": "circle",
        "title": "改考换书的预警信号",
        "conclusion": (
            "改考有前兆可盯：一是5-8月院校或学院官网单独发布的初试科目调整预告，早于9月正式简章；"
            "二是上一年临近报名才临时改科目、缩招，说明该专业调整压力大，今年再改概率高；"
            "三是院系重组、学科评估、专业拆分合并常伴随科目调整；四是参考书多年未更新或培养方案改革。"
            "核对关键点是科目代码，代码变基本等于考试内容变。"
        ),
        "conditions": (
            "适用于7-9月专业目录集中发布期；网传小道消息不可作为换校依据，一切以官网正式文件为准。"
        ),
        "counterexample": (
            "部分院校从不预告、9月直接换书改考；也有预告「拟调整」后在正式简章中微调甚至收回，"
            "预告不等于定稿。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "新东方网：专业目录变动预警——如何第一时间发现目标院校的「改考」信号", "url": "https://mtoutiao.xdf.cn/kaoyan/202608/15358643.html", "supports": "暑期预公告先于正式简章、科目代码变化即内容变化、三层监测渠道"},
            {"title": "启航考研：专业目录变动预警——如何提前发现目标院校「改考」信号", "url": "https://jixun.iqihang.com/zixun/changshi/2026799313.html", "supports": "上年临时变动预示再改概率高、院系调整是前兆"},
            {"title": "新东方网：27考研招生简章「避坑三读」", "url": "https://kaoyan.xdf.cn/202609/15369559.html", "supports": "逐字比对科目代码与参考书四类变化"},
        ],
    },
    {
        "question_id": "C3",
        "category": "circle",
        "title": "提前摸清导师名额",
        "conclusion": (
            "提前判断靠三步：一查官方，部分院校招生专业目录直接标注各导师名额，"
            "导师个人主页常设「招生信息」栏写明每年招收人数，导师是否连续出现在当年招生导师名单是硬信号；"
            "二问在读学长学姐，能问到导师今年实际名额与组内情况；三发邮件附简历直接向导师确认。"
            "注意「欢迎报考」属客套话，不代表有名额。"
        ),
        "conditions": (
            "适用于初试前后联系导师阶段；导师名单类信息以当年学院官网发布为准，往年数据只能作参考。"
        ),
        "counterexample": (
            "有的导师因名额被推免占满或当年项目变动临时不招，凭往年推测可能落空，"
            "最终以导师本人或招生办确认为准。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "知小道经验网：怎么看导师招不招研究生", "url": "https://www.zhixiaodao.com/article/4665065834e36fb449e5f8ed.html", "supports": "招生计划可标注导师姓名、拟录取后邮件确认"},
            {"title": "艾思科蓝：考研放榜，抢导师大战正式开启", "url": "https://www.ais.cn/news/recruit/9508", "supports": "师兄师姐可问到当年名额数目、官网为权威入口"},
            {"title": "中国科学院大学导师个人主页示例（刘康）", "url": "https://people.ucas.ac.cn/~liukang", "supports": "导师主页设招生信息栏、写明每年招收名额的真实实例"},
        ],
    },
    {
        "question_id": "C4",
        "category": "circle",
        "title": "水旱区：部分真实",
        "conclusion": (
            "现象部分真实：公共课由报考院校所在省份统一组织阅卷，各省主观题给分尺度确有差异，"
            "网传旱区（京沪苏等）与水区的差距约每科3-8分；但无官方划分、流传版本互相矛盾，"
            "且同省所有考生标准一致，对考同校同专业者影响很小，主要影响跨省调剂时的分数观感。"
            "专业课由招生单位自阅，院校间给分差异比省际差异更值得注意。"
        ),
        "conditions": (
            "仅指公共课及统考科目的主观题部分，客观题机器阅卷无差异；"
            "适合估分与调剂时参考，不应作为择校核心依据。"
        ),
        "counterexample": (
            "水旱并非固定：有省份前一年大旱次年转水的网传翻转，"
            "热门专业报考扎堆时「全域皆旱」，水区红利消失。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "天津新东方：考研「水区旱区」真的存在吗？", "url": "https://www.jiaoyubao.cn/news/n410527.html", "supports": "差异客观存在但约3-5分、无官方数据、主要影响调剂"},
            {"title": "都学课堂：考研「水旱区」大洗牌", "url": "https://www.doxue.com/information/15471", "supports": "水旱仅存在于主观题、无官方标准且版本混乱"},
            {"title": "网易号：水旱区有大变动？", "url": "https://www.163.com/dy/article/KPUFBLML0516BKJI.html", "supports": "主观题差5-8分、热门专业全域皆旱"},
            {"title": "考研论坛（暨大考研帖）：考研水旱区是什么？有什么影响？", "url": "http://bbs.kaoyan.com/forum.php?extra=page%3D1&mod=viewthread&tid=10468914", "supports": "公共课由报考院校所在省统一评卷、专业课由招生单位自阅的制度事实"},
        ],
    },
    {
        "question_id": "C5",
        "category": "circle",
        "title": "自命题真题搜寻渠道",
        "conclusion": (
            "官方不公布不等于找不到，按优先级找：一查目标院校研究生院及学院官网，"
            "少数院校（如暨南大学、山东大学等）直接公布历年真题或样题；"
            "二找直系上岸学长学姐拿回忆版，QQ考研群、微博超话、小红书是主要入口；"
            "三查校内打印店与图书馆试卷存档；四走电商二手平台但须平台担保交易。"
            "回忆版需多版本交叉核验，所谓「内部绝密真题」一律是骗局。"
        ),
        "conditions": (
            "适用于自命题专业课；统考专业课（如408、311、396）真题公开易得，无需走此流程。"
        ),
        "counterexample": (
            "多数院校出于保密不再公开真题，官网找不到属常态；"
            "回忆版题干常有缺失和记忆偏差，不能当原卷用于模拟估分。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "广工考研论坛：还不知道该去哪里寻找专业课真题，这篇文章全部告诉你", "url": "https://www.gdutkaoyan.com/kaoyanfudao-1884-1-1.html", "supports": "官网公布真题的院校实例与学长学姐/打印店/电商渠道"},
            {"title": "启航考研：自命题专业课真题怎么搜集？渠道甄别、资料使用全指南", "url": "https://jixun.iqihang.com/zixun/changshi/2026793733.html", "supports": "图书馆存档、多版本交叉核验、「命题组流出」均属骗局"},
            {"title": "启航考研：28考研专业课自命题怎么找资料", "url": "https://m-jixun.iqihang.com/zixun/changshi/2026797385.html", "supports": "邮件咨询研招办、回忆版仅有题干梗概的局限"},
        ],
    },
    {
        "question_id": "C6",
        "category": "circle",
        "title": "复试口语高频题单",
        "conclusion": (
            "高频问题集中在五类：自我介绍（约1-3分钟，几乎必考）、考研原因及为什么选本校本专业、"
            "研究生阶段学习规划、毕业后职业规划（如毕业五年打算）、个人背景类（家乡、家庭、本科院校、优缺点、兴趣爱好）。"
            "部分院校还会考抽题演讲、短文朗读翻译或用英语提问专业问题。"
            "备考要点是答案与自我介绍呼应、避免明显背诵痕迹。"
        ),
        "conditions": (
            "考查形式与分值占比因校而异，以报考院校当年复试细则为准；院校越好英语考查难度一般越高。"
        ),
        "counterexample": (
            "不少学校为防背模板已取消自我介绍环节，改用随机日常问答或英语专业提问代替，"
            "只背通用模板容易失手。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "新东方网：考研复试英语口语常见问题及应答模板", "url": "https://www.xdf.cn/1010/202602/15103215.html", "supports": "五大类问题划分及典型英文问法"},
            {"title": "CSDN：保研面试/考研复试英语口语常见问题整理", "url": "https://blog.csdn.net/weixin_43595277/article/details/120519303", "supports": "数十个真实高频问题清单"},
            {"title": "bilibili：一文搞定考研复试英语！（厚大法硕）", "url": "https://www.bilibili.com/opus/1020688725853601792", "supports": "口语三种考查形式（自我介绍/读译/自由问答）与防模板提醒"},
        ],
    },
    # ---------------- D 组·内幕实锤 ----------------
    {
        "question_id": "D1",
        "category": "evidence",
        "title": "压分判定实锤法",
        "conclusion": (
            "压分现象在部分院校确实存在，网传多集中于调剂热门院校与部分文科自命题专业，"
            "但把「题目难、标准高」误判为压分的情况也常见。实锤判定须用官方公示数据："
            "一志愿复试名单专业课分数普遍异常低（文科普遍不过百）而公共课成绩正常；"
            "拟录取名单中调剂生占比高、一志愿过线者极少；且连续2-3年重复出现而非单年波动，才可下结论。"
        ),
        "conditions": (
            "判定须用近2-3年一志愿复试名单与拟录取名单对照，单一年份不构成实锤；"
            "部分院校存在「压分大小年」波动。"
        ),
        "counterexample": "顶尖院校专业课给分严可能源于学术标准高而非留名额给调剂，均分低不必然等于压分。",
        "confidence": "multi_source",
        "sources": [
            {"title": "新东方网：这13所院校压分严重，慎选！", "url": "https://kaoyan.xdf.cn/202502/14059435.html", "supports": "压分定义（普遍低分而非个别）与拟录取名单判定法"},
            {"title": "今日头条：考研择校怕踩坑？3步教你识破目标院校压分套路", "url": "https://www.toutiao.com/article/7553230979259793974/", "supports": "复试线异常、专业课与公共课反差、一志愿调剂占比三步判定"},
            {"title": "聚创考研网：考研专业课压分，不保护一志愿考生？", "url": "https://www.juyingonline.com/news/316796.html", "supports": "对比往年复试名单专业课分数、压一志愿招优质调剂的动机"},
            {"title": "网传23考研这些院校压分严重（转载）", "url": "http://www.yibiao.ozhou.com.cn/zixun/2023/0420/2365.html", "supports": "「文科专业课多数上三位数即不压分」量化参考线与两种压分形式区分"},
        ],
    },
    {
        "question_id": "D2",
        "category": "evidence",
        "title": "双非歧视判定法",
        "conclusion": (
            "需中性表述：复试打分环节对双非出身的偏见多属个体行为、无明文规则，个案难以实锤；"
            "但院校层面的「出身偏好」有据可查——有研究统计约三成高校在调剂原则中写明优先接收985/211生源，"
            "个别学院调剂公告曾直接限定本科出身。判定方法：对比复试与录取名单中被刷者是否集中于高分双非考生、"
            "调剂录取者的本科院校构成、复试占比是否过高。"
        ),
        "conditions": (
            "适用于择校与调剂决策；初试为匿名统改基本无歧视空间，"
            "指控应落在可查证的公示数据而非个人感受上。"
        ),
        "counterexample": (
            "同校考生体验可能相反：遇公平老师与遇偏好出身的老师结论完全不同，"
            "单一高分被刷案例不足以证明院校性歧视。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "澎湃新闻·网易数读：985研究生，救不了本科双非", "url": "https://www.thepaper.cn/newsDetail_forward_17180693", "supports": "研究统计约30%高校调剂原则优先985/211生源的硬证据"},
            {"title": "MBAChina：考研择校避坑指南——如何判断院校是否歧视双非", "url": "https://www.mbachina.com/html/xw/202508/627711.html", "supports": "四步判定法（分数差/调剂公告/学长学姐/复试占比）"},
            {"title": "CSDN·计算机考研：双非会被歧视？计算机考研复试真相！", "url": "https://blog.csdn.net/csseky/article/details/115059815", "supports": "歧视多无明文规则属教师个体行为、刷一志愿收调剂可由名单分析发现"},
        ],
    },
    {
        "question_id": "D3",
        "category": "evidence",
        "title": "一志愿保护可验证",
        "conclusion": (
            "真实存在且可官方验证。保护一志愿的院校通常有三种公开表现：生源足够时明确公告不接收（校外）调剂"
            "或只收校内调剂；一志愿先复试先录取，剩余名额才给调剂；一志愿与调剂生分开排名、分开计算成绩。"
            "判定直接查当年《复试录取办法》原文与拟录取名单考生编号构成，多所985/211有公开公告可查。"
            "但保护一志愿不等于进复试就录取，差额复试照样淘汰。"
        ),
        "conditions": (
            "适用于择校评估与调剂策略；公告须逐年核对，往年保护不代表今年延续。"
        ),
        "counterexample": (
            "个别院校反向操作：压一志愿专业课分数或提高单科线，腾出名额接收高分调剂生，"
            "需结合名单交叉识别。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "中国教育在线：不接收「校外调剂」？这些院校明确规定！", "url": "https://kaoyan.eol.cn/nnews/202403/t20240327_2576322.shtml", "supports": "暨南大学/武汉大学/南大商学院等校公告不接收校外调剂的事实"},
            {"title": "都学课堂：院校白名单——保护一志愿！", "url": "https://www.doxue.com/knowledge-15519.html", "supports": "保护一志愿的四种官方表现与院校实例"},
            {"title": "启航考研：简单几步，判断目标院校是否保护第一志愿", "url": "https://m-jixun.iqihang.com/zixun/changshi/2026794780.html", "supports": "复试时间线与拟录取名单编号判定法、保护≠录取的提醒"},
        ],
    },
    {
        "question_id": "D4",
        "category": "evidence",
        "title": "差额比看刷人力度",
        "conclusion": (
            "复试刷人是制度性的：教育部规定复试应采取差额形式，差额比例一般不低于120%，"
            "即至少约六分之一进复试者被刷；生源充足的院校可上调至1.5:1甚至2:1，个别热门专业出现过1:3的高淘汰。"
            "比例越高，初试排名靠后者风险越大。查法：招生简章或复试录取办法中公布的差额比例，"
            "以及往年复试名单人数与拟录取人数之比。"
        ),
        "conditions": (
            "多数院校实际执行1.2-1.5之间；生源不足的专业会等额复试（1:1），"
            "进入复试不等于安全，复试不合格仍会被刷。"
        ),
        "counterexample": (
            "部分院校专业实行等额复试（如某年浙江大学软件学院83个名额83人进复试），"
            "但等额下复试不合格同样会被淘汰。"
        ),
        "confidence": "official",
        "sources": [
            {"title": "中国教育在线：硕士研究生复试录取比例是多少？", "url": "https://kaoyan.eol.cn/nnews/202401/t20240130_2557237.shtml", "supports": "教育部1:1.2至1:1.4复试比例规定"},
            {"title": "研招网转载：山东大学2025年硕士研究生招生考试考生进入复试的初试成绩基本要求", "url": "https://yz.chsi.com.cn/kyzx/fsfsx34/202503/20250313/2293357952.html", "supports": "「复试差额比例一般不低于120%」官方规定原文"},
            {"title": "MBA百科问答：考研差额复试淘汰比例有国家规定吗？", "url": "https://xue.aimcx.com/queinfo-78677.html", "supports": "120%为下限、上不封顶及1:2甚至1:3高差额案例"},
            {"title": "MBAChina：基本不刷人！这些院校2024考研施行等额复试", "url": "https://www.mbachina.com/html/xw/20240322/581360.html", "supports": "浙江大学软件学院等额复试实例与例外情形"},
        ],
    },
    {
        "question_id": "D5",
        "category": "evidence",
        "title": "拟录取名单读法",
        "conclusion": (
            "官方公示的拟录取名单可读出四层信息：一看考生编号前5位（一志愿报考院校代码），"
            "编号一致说明一志愿录取为主、大概率不收校外调剂，大量外校代码说明调剂占比高；"
            "二比实际录取人数与计划招生人数，判断是否临时扩招；三看录取最低分与复试线的差距，"
            "判断复试是否高分扎堆、复试线是否只是「表面温柔」；四看专业课分数分布，辅助判断给分松紧。"
        ),
        "conditions": (
            "名单在院校研究生院官网及研招网信息公开平台公示，部分院校公示期满即删除，查到后应及时存档。"
        ),
        "counterexample": (
            "编号混杂不必然是压分抢调剂：也可能是专业冷门报考人数少只能录调剂，"
            "需结合一志愿上线人数与专业课均分再下结论。"
        ),
        "confidence": "multi_source",
        "sources": [
            {"title": "乐米网：考研择校小妙招——巧用录取名单中的考生编号", "url": "https://www.7k7x.com/wenzhang/a3c3fac0-86db-11f0-97c6-b3e313951f41", "supports": "编号前5位判一志愿/调剂、两种解释需甄别"},
            {"title": "知乎回答：如何获取考研调剂院校信息？", "url": "https://www.zhihu.com/tardis/bd/ans/2343777012", "supports": "用前两年拟录取名单判断是否收调剂与竞争度"},
            {"title": "启航考研：简单几步，判断目标院校是否保护第一志愿", "url": "https://m-jixun.iqihang.com/zixun/changshi/2026794780.html", "supports": "看编号构成与一志愿占比、识别风险信号"},
            {"title": "研招网·全国硕士研究生招生信息公开平台", "url": "https://yz.chsi.com.cn/zsgs/", "supports": "官方公示渠道及公开范围规则"},
        ],
    },
]


def seed_intel_cards(db: Session) -> tuple[int, int]:
    """幂等导入门道卡：按 (question_id, title) 去重，已存在跳过。

    Returns:
        (inserted, skipped)
    """
    inserted = 0
    skipped = 0
    existing = {
        (c.question_id, c.title)
        for c in db.query(IntelCard.question_id, IntelCard.title).with_entities(
            IntelCard.question_id, IntelCard.title
        )
    }
    for spec in _CARDS:
        key = (spec["question_id"], spec["title"])
        if key in existing:
            skipped += 1
            continue
        db.add(
            IntelCard(
                track=_TRACK,
                category=spec["category"],
                question_id=spec["question_id"],
                question_text=_QUESTION_TEXT[spec["question_id"]],
                title=spec["title"],
                conclusion=spec["conclusion"],
                conditions=spec["conditions"],
                counterexample=spec["counterexample"],
                confidence=spec["confidence"],
                sources=spec["sources"],
                as_of=_AS_OF,
            )
        )
        inserted += 1
    db.commit()
    logger.info("门道卡 seed 完成：新增 %d，跳过 %d（共 %d 张定义）", inserted, skipped, len(_CARDS))
    return inserted, skipped
