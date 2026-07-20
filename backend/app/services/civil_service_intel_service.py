"""考公作战室服务层 — 岗位情报 + 考公定位 + 考公暗知识。

借鉴 career_intel_service 的三段式结构，覆盖考公全流程的信息差。
"""
import json
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.civil_service_intel import CivilServiceDarkKnowledge, CivilServicePositioning, PostIntel
from app.services.ai_orchestrator import AIOrchestrator


# ===== 考公暗知识种子数据 =====
CIVIL_SERVICE_DARK_KNOWLEDGE_SEED = [
    # ===== 第一阶段：大一准备 =====
    {
        "stage": "early_prep",
        "category": "赛道选择",
        "title": "国考vs省考vs选调生vs事业编：四条赛道本质差异",
        "content": "国考是中央垂直管理单位招人，薪资由中央财政+地方补贴构成，基本工资全国统一但绩效补贴差异大（如深圳海关比中西部海关绩效高2000+/月）；省考薪资完全依赖地方财政，苏州、杭州等地年终绩效可比中西部县乡全年收入高1-2万；选调生是党政领导干部后备人选，需下基层2-3年但晋升速度显著快于普通公务员；事业编走职称路线，车补等补贴通常缺失。",
        "importance": "critical",
        "common_misconception": "很多人以为国考待遇全国统一、选调生就是高级公务员、事业编和公务员差不多。",
        "actionable_advice": "法学/计算机/财会专业优先冲国考税务、海关；想晋升快且符合条件优先走定向选调；求稳且专业冷门可考虑事业编，但需接受待遇和晋升天花板。",
        "verification_method": "对比目标地区近3年招录公告职位表；咨询当地在职人员到手收入（含公积金、年终奖）。",
        "tags": ["国考", "省考", "选调生", "事业编", "赛道选择"],
        "sort_order": 1,
    },
    {
        "stage": "early_prep",
        "category": "选调条件",
        "title": "选调生的三重隐性门槛：党员+学生干部+校级荣誉",
        "content": "90%以上选调岗位要求中共党员（含预备党员），附加1年以上学生干部经历或校级以上奖励；班委通常不算学生干部，需班长/团支书/学生会副部长以上；绝大多数省份仅面向当年应届毕业生；定向选调通常限定双一流高校范围。",
        "importance": "critical",
        "common_misconception": "以为毕业2年内没交社保就算应届、以为只要是学生干部就行。",
        "actionable_advice": "大一下学期争取入党积极分子→大三前成为预备党员；至少担任班长/团支书满1年；争取校级荣誉。",
        "verification_method": "查阅目标省份近2年选调生公告原文选调条件章节；向本校就业指导中心确认是否在选调高校名单内。",
        "tags": ["选调生", "党员", "学生干部", "双一流"],
        "sort_order": 2,
    },
    {
        "stage": "early_prep",
        "category": "应届生身份",
        "title": "应届生身份：67%国考岗位专供，三不限竞争500:1",
        "content": "2025年国考67%岗位明确面向应届毕业生，浙江省考释放近6成名额给应届生，选调生100%仅限应届；应届生岗位竞争比普遍20:1以内，而往届生三不限岗位动辄500:1甚至上千比一；多数省份择业期未缴社保仍算应届，但部分省份要求严格。",
        "importance": "critical",
        "common_misconception": "以为应届生身份不值钱、边工作边考也一样、交了社保还是应届。",
        "actionable_advice": "毕业前一年9月国考到次年4月省考联考是黄金期，全力备考；若首战失利可申请暂缓就业/不缴社保保留2年择业期。",
        "verification_method": "统计近2年国考/目标省考职位表中仅限应届岗位占比；电话咨询招录单位择业期应届认定标准。",
        "tags": ["应届生", "国考", "竞争比", "择业期"],
        "sort_order": 3,
    },
    {
        "stage": "early_prep",
        "category": "专业选择",
        "title": "考公四大王牌专业：法学/汉语言/计算机/财会",
        "content": "法学可报岗位最多（法院、检察院、司法局、税务、海关、公安等），汉语言文学是写材料必备（两办组纪宣都要），计算机是数字化转型刚需（各单位信息中心），财会/审计是财政局、审计局、税务局主力；工科和文科冷门专业岗位极少，往往只能报三不限。",
        "importance": "high",
        "common_misconception": "以为什么专业都能考公、专业影响不大。实际上专业决定了你能报的岗位数量和竞争激烈程度。",
        "actionable_advice": "大一大二有机会优先转专业到考公友好专业；转不了就辅修或跨考相关专业研究生。",
        "verification_method": "下载近3年国考/省考职位表，按专业筛选统计可报岗位数量。",
        "tags": ["专业", "法学", "汉语言", "计算机", "财会"],
        "sort_order": 4,
    },

    # ===== 第二阶段：备考选岗 =====
    {
        "stage": "preparation",
        "category": "地区待遇",
        "title": "地区待遇差3-5倍：江浙沪vs中西部真实差距",
        "content": "同一级别的科员，苏南、浙江、珠三角地区到手+公积金普遍20-35万/年（苏州工业园、深圳部分区可达40万+）；中西部普通地市到手仅6-10万/年，部分财政困难县乡可能拖欠绩效；即使是国考岗位，地区附加津贴差异巨大。",
        "importance": "critical",
        "common_misconception": "以为公务员工资都阳光了全国差不多、基本工资就是全部收入。",
        "actionable_advice": "经济条件普通的家庭优先考虑长三角、珠三角发达地区；若选家乡岗位优先选市区/经开区而非乡镇。",
        "verification_method": "在QZZN论坛、小红书搜索XX地区公务员到手收入；咨询当地3年以上在职人员（问清到手+公积金+年终全包数）。",
        "tags": ["待遇", "地区差异", "江浙沪", "珠三角"],
        "sort_order": 5,
    },
    {
        "stage": "preparation",
        "category": "部门梯队",
        "title": "部门权力与待遇梯队：两办组纪宣vs清水衙门",
        "content": "第一梯队（两办=党委办+政府办、组织部、纪委监委、宣传部）：掌握核心权力，晋升最快，纪委有办案补贴600-1200元/月；第二梯队（发改委、财政局、住建局、政法委）：掌握项目审批/资金分配权，待遇优厚；第三梯队（教育局、卫健局、人社局）：中等实权部门；清水衙门（档案局、老干部局、科协、文联）：工作清闲但晋升慢待遇一般。",
        "importance": "high",
        "common_misconception": "只看单位名字好听，以为都是公务员待遇差不多。",
        "actionable_advice": "追求政治前途优先冲两办组纪宣（但加班极多）；想兼顾生活选教育局、卫健局等中等部门；求清闲选群团、档案局等。",
        "verification_method": "查看目标单位近3年干部提拔公示名单频率；咨询在职人员忙不忙、年终绩效系数。",
        "tags": ["部门选择", "两办", "晋升", "清水衙门"],
        "sort_order": 6,
    },
    {
        "stage": "preparation",
        "category": "竞争比真相",
        "title": "报录比会骗人：平均98:1是被三不限拉高的",
        "content": "2026年国考平均竞争比98:1，但这是平均陷阱——应届生专属岗位竞争比普遍10:1~30:1，而三不限往届岗位可高达2040:1；限制专业+学历+应届+政治面貌的岗位实际竞争可能仅10:1。",
        "importance": "high",
        "common_misconception": "看到平均竞争比86:1就觉得自己没戏、盲目追捧报录比低的冷门岗位。",
        "actionable_advice": "用限制条件数量判断真实竞争；不要迷信报名最后一天的人数统计（大量审核未通过数据未显示）。",
        "verification_method": "下载近2年目标省份报名人数统计表，按条件筛选后计算限定条件岗位的真实竞争比。",
        "tags": ["报录比", "竞争", "三不限"],
        "sort_order": 7,
    },
    {
        "stage": "preparation",
        "category": "萝卜坑识别",
        "title": "萝卜坑岗位四大特征：条件诡异+人数极少+发布时间异常",
        "content": "萝卜岗核心特征：①限制条件超过3项且组合罕见；②低岗高配或条件逻辑矛盾（如28岁以下+5年基层工作经历）；③非窗口岗位强行限制本地户籍/方言；④公告发布时间诡异、报名期极短（1-2天）；⑤只招1人且条件极其具体。",
        "importance": "critical",
        "common_misconception": "以为条件多就是萝卜岗、国考省考没有萝卜岗、人才引进更公平。",
        "actionable_advice": "优先选招录3人以上的岗位（批量招录内定概率指数级下降）；优先选国考/省考联考等统考岗位（双盲面试作弊成本极高）。",
        "verification_method": "将岗位条件复制到公考雷达等平台查看匹配人数；查看该单位历年招录名单是否集中在某一学校/地区。",
        "tags": ["萝卜坑", "内定", "岗位识别"],
        "sort_order": 8,
    },
    {
        "stage": "preparation",
        "category": "编制差异",
        "title": "参公编制≠行政编：流动时才见分晓",
        "content": "参公人员本质是事业编制但参照公务员法管理，薪酬待遇与行政编几乎一致；核心差异在跨单位调动：参公人员调入纯行政单位存在政策障碍，部分地区参公人员无法参加面向公务员的遴选；机构改革中参公单位可能被划为公益类事业单位失去参公身份。",
        "importance": "high",
        "common_misconception": "以为参公就是公务员、待遇一样就没区别。",
        "actionable_advice": "同地区同级别优先选行政编；参公适合追求稳定且不打算跨系统调动的人。",
        "verification_method": "查看职位表编制性质栏是否标注参照公务员法管理；咨询当地组织部门参公转任行政编的实际案例。",
        "tags": ["参公", "行政编", "事业编", "编制差异"],
        "sort_order": 9,
    },
    {
        "stage": "preparation",
        "category": "服务期",
        "title": "五年服务期：不是乡镇专属的卖身契",
        "content": "2019年起中组部规定所有新录用公务员在机关最低服务5年（含试用期），并非仅乡镇岗位；服务期内不得辞职（强行辞职按辞退处理5年内不得报考公务员）、不得参加遴选、调动极其困难。",
        "importance": "critical",
        "common_misconception": "以为服务期只是说说而已、考上了再想办法调动、只有乡镇有服务期。",
        "actionable_advice": "报考前仔细看职位表备注栏是否标注最低服务年限；若不想在报考地长期发展慎报有明确服务期的岗位。",
        "verification_method": "查阅新录用公务员任职定级规定第六条；电话咨询招录单位服务期内能否参加遴选/调动。",
        "tags": ["服务期", "五年", "辞职", "遴选"],
        "sort_order": 10,
    },
    {
        "stage": "preparation",
        "category": "异地考公",
        "title": "考公不异地、异地不乡镇",
        "content": "异地基层公务员面临多重困境：语言不通（南方方言区尤为明显）、人脉从零开始本土干部晋升天然占优、回家成本高、婚恋买房照顾父母全靠自己、方言圈子融不进。北方人慎选南方方言区基层岗。",
        "importance": "critical",
        "common_misconception": "以为现在高铁方便想家随时回、先上岸再说以后调动。",
        "actionable_advice": "牢记考公不异地、异地不乡镇铁律；若考异地优先选省会/副省级城市而非县乡。",
        "verification_method": "在社交平台搜索异地公务员辞职真实经历；实地走访目标单位了解外地人占比。",
        "tags": ["异地", "乡镇", "方言", "调动"],
        "sort_order": 11,
    },

    # ===== 第三阶段：笔试面试 =====
    {
        "stage": "exam",
        "category": "报名策略",
        "title": "不要最后一天下午报名：审核不通过可能无法改报",
        "content": "国考报名资格审核通常需要1-2天，如果最后一天下午才报名，审核不通过时报名已截止无法改报其他岗位；报名选中间时段（观察2天报名人数再选）更合理。",
        "importance": "high",
        "common_misconception": "以为最后一天看清楚人数再报最聪明。",
        "actionable_advice": "报名选第3-4天，先观察各岗位报名人数趋势，留出审核不通过的改报时间。",
        "verification_method": "查看每年国考报名截止后因审核不通过错失机会的考生案例。",
        "tags": ["报名", "审核", "时间节点"],
        "sort_order": 12,
    },
    {
        "stage": "exam",
        "category": "政审范围",
        "title": "政审不止查自己：直系亲属有这些记录直接影响",
        "content": "普通岗位政审审查考生本人+父母+配偶+子女；政法类（公检法国安）、涉密岗位审查三代直系亲属；直系亲属有危害国家安全、恐怖活动、贩毒等八大重罪记录、被开除公职、列为失信被执行人会直接影响录取；父母醉驾被刑事处罚会影响政法类岗位。",
        "importance": "critical",
        "common_misconception": "以为政审只查自己、父母酒驾/行政拘留影响考公（普通交通肇事一般不影响，醉驾被刑事处罚会影响）。",
        "actionable_advice": "报考公检法等严格岗位前先了解直系亲属是否有刑事犯罪记录；档案材料确保真实（年龄学历党龄造假会被一票否决）。",
        "verification_method": "查阅公务员录用考察办法；咨询当地招录单位政审查询范围。",
        "tags": ["政审", "直系亲属", "犯罪记录", "公检法"],
        "sort_order": 13,
    },
    {
        "stage": "exam",
        "category": "体检暗坑",
        "title": "这些小问题可能让你笔试第一被刷",
        "content": "血压：紧张导致血压高直接不合格（可提前低盐饮食+作息调整）；色盲色弱：公安海关食品检验岗位直接一票否决；纹身：警察司法岗位任何部位纹身不合格；转氨酶/血糖：熬夜饮酒会导致偏高被要求复检；执法岗要求裸眼视力4.8以上。",
        "importance": "critical",
        "common_misconception": "以为自己身体好肯定没问题、体检就是走个形式。",
        "actionable_advice": "笔试结束后立即去三甲医院做公务员录用体检套餐预检；体检前1周不熬夜不喝酒不吃油腻。",
        "verification_method": "对照公务员录用体检通用标准和特殊标准逐条自查；保存预检报告对比。",
        "tags": ["体检", "血压", "色盲", "纹身", "预检"],
        "sort_order": 14,
    },
    {
        "stage": "exam",
        "category": "面试公平性",
        "title": "国考省考面试几乎无操作空间",
        "content": "国考/省考联考面试实行双盲抽签+异地考官调配制度：考生抽签决定考场和顺序，考官抽签决定考场，7名考官打分去掉最高最低取平均；但事业单位单招、人才引进面试（免笔试直接面试）存在一定操作空间。",
        "importance": "high",
        "common_misconception": "以为面试全靠关系、笔试第一也会被黑。",
        "actionable_advice": "放心备考笔试面试，国考省考公平性有制度保障；但事业单位单招、人才引进需谨慎评估。",
        "verification_method": "了解目标考试的面试组织形式（是否异地考官、是否当场出分）。",
        "tags": ["面试", "公平性", "双盲", "人才引进"],
        "sort_order": 15,
    },
    {
        "stage": "exam",
        "category": "事业编分类",
        "title": "事业编联考vs单招：公平性天差地别",
        "content": "事业单位全国联考/全省统考公平性接近省考；但单位自行组织的单招、人才引进（尤其是免笔试直接面试）存在较大操作空间；事业编分类：全额拨款（最稳定）>差额拨款>自收自支（改革中可能转企）。",
        "importance": "high",
        "common_misconception": "以为事业编考试都一样、人才引进学历高就公平。",
        "actionable_advice": "优先选择事业单位联考岗位；单招岗位如果条件奇怪建议避开；报考前确认单位性质是否为全额拨款。",
        "verification_method": "查看招聘公告是人社厅统一组织还是单位自行组织；了解目标单位在事业单位改革中的分类方向。",
        "tags": ["事业编", "联考", "单招", "人才引进"],
        "sort_order": 16,
    },
    {
        "stage": "exam",
        "category": "档案问题",
        "title": "档案小瑕疵可能成为政审杀手",
        "content": "政审严格审查个人档案，常见问题：年龄前后不一致（入团/入学/入党材料年龄冲突）、学历材料缺失、党龄材料不规范、奖惩材料矛盾、档案在自己手里（死档）。",
        "importance": "high",
        "common_misconception": "以为档案在人才中心就没问题、材料有点小瑕疵没关系。",
        "actionable_advice": "大四毕业前核对自己的档案材料是否齐全规范；档案不要个人携带通过机要通道转递。",
        "verification_method": "在政审前申请查看个人档案；对照干部人事档案工作条例自查。",
        "tags": ["档案", "政审", "材料缺失"],
        "sort_order": 17,
    },
    {
        "stage": "exam",
        "category": "社保与应届",
        "title": "社保记录对应届生身份的影响因省而异",
        "content": "国考认定应届生一般不看社保（毕业两年择业期内即使交过社保仍可报部分应届岗）；但省考差异极大——北京上海等地上过社保就不算应届；浙江2025年明确不要求未就业；企业缴纳社保记录在资格复审和政审时可被查到。",
        "importance": "high",
        "common_misconception": "以为交了社保就一定不是应届、只要没签三方就算应届。",
        "actionable_advice": "如果想保留应届生身份毕业2年内尽量不缴职工社保；报考前电话咨询招录单位社保记录是否影响认定。",
        "verification_method": "仔细阅读目标省份报考指南应届毕业生界定章节；拨打招录单位咨询电话录音确认。",
        "tags": ["社保", "应届生", "择业期"],
        "sort_order": 18,
    },

    # ===== 第四阶段：入职适应 =====
    {
        "stage": "onboarding",
        "category": "试用期规则",
        "title": "试用期取消录用不是双向选择那么简单",
        "content": "公务员试用期1年，考核不合格会被取消录用；试用期主动申请取消录用无服务期约定一般不影响后续报考；但若有服务期约定试用期不得辞职，强行离职需付违约金并记入诚信档案5年内不得报考；被取消录用（考核不合格）和主动申请取消性质不同。",
        "importance": "critical",
        "common_misconception": "以为试用期可以随便走、取消录用就是辞退。",
        "actionable_advice": "入职前充分了解岗位情况不要盲目上岸后又反悔；若确需放弃尽量在试用期内以书面形式申请。",
        "verification_method": "查阅新录用公务员试用期管理办法；咨询目标省份组织部关于试用期取消录用的具体政策。",
        "tags": ["试用期", "取消录用", "诚信档案"],
        "sort_order": 19,
    },
    {
        "stage": "onboarding",
        "category": "待遇组成",
        "title": "公务员全包收入：基本工资只是零头",
        "content": "全包收入=基本工资（全国统一科员约2500-3500元/月，占比20-30%）+规范性津贴补贴+车补（科员500-650元/月，事业编通常没有）+公积金（双边12%-24%，发达地区可达5000+/月）+年终一次性奖金+绩效考核奖+其他补贴。",
        "importance": "high",
        "common_misconception": "只问每月到手多少、以为基本工资3000就是全部收入。",
        "actionable_advice": "咨询待遇时一定要问全包（到手+公积金+年终）；关注目标地区财政状况。",
        "verification_method": "查看当地财政预算公开报告中人员经费部分；找3位以上不同部门在职人员交叉验证。",
        "tags": ["待遇", "公积金", "绩效", "车补"],
        "sort_order": 20,
    },
    {
        "stage": "onboarding",
        "category": "借调陷阱",
        "title": "借调≠调动：干活有你好处没你",
        "content": "借调编制人事关系考核权晋升权都在原单位，人只是去上级单位干活；长期借调（3-5年）典型结局：原单位把你当外人晋升评优不考虑，借调单位领导口头承诺帮你协调编制但大多是空话，最后两头落空被退回。",
        "importance": "high",
        "common_misconception": "以为被上级借调是领导器重、借调就是镀金、领导承诺就靠谱。",
        "actionable_advice": "无书面借调文件/明确转任时间表的借调一律谨慎接受；借调期以3-6个月为限超过1年无落编迹象立即申请回原单位。",
        "verification_method": "问清借调期限是否有正式借调函；了解本单位历史上借调人员的最终去向。",
        "tags": ["借调", "调动", "编制", "陷阱"],
        "sort_order": 21,
    },
    {
        "stage": "onboarding",
        "category": "试用期考核",
        "title": "试用期不是保险箱：6种情形可取消录用",
        "content": "试用期满考核有德能勤绩廉五项，不合格将被取消录用；不履行公务员义务、不遵守纪律、无法达到岗位要求、道德品行不佳、因个人原因无法正常履职、档案材料造假等均可能导致不合格。",
        "importance": "medium",
        "common_misconception": "以为考上就万事大吉、试用期没人管。",
        "actionable_advice": "入职后低调做事遵守工作纪律；不要在试用期内犯重大错误或长期旷工；尽快熟悉业务。",
        "verification_method": "查阅新录用公务员试用期管理办法。",
        "tags": ["试用期", "考核", "取消录用"],
        "sort_order": 22,
    },
    {
        "stage": "onboarding",
        "category": "试用期纪律",
        "title": "入职收费全是骗局，正规单位不收任何费用",
        "content": "体制内入职不收取任何费用（岗前培训费、体检费、工装费全免或报销）；任何要求入职前交钱的都是骗子；体检费通常由单位承担。",
        "importance": "critical",
        "common_misconception": "有些考生以为体制内入职也需要像某些企业一样交押金。",
        "actionable_advice": "任何要求交钱的通知直接拒绝并向招录单位核实；通过官方渠道获取入职通知。",
        "verification_method": "对比官方招录公告和通知；拨打招录单位官方电话核实。",
        "tags": ["入职", "收费", "骗局"],
        "sort_order": 23,
    },

    # ===== 第五阶段：职业发展 =====
    {
        "stage": "career_dev",
        "category": "遴选真相",
        "title": "遴选：普通人最公平的上升通道，但也有坑",
        "content": "遴选是基层公务员向上流动的主渠道，中央遴选公平性最高（双盲阅卷、考官跨省调配、监控接入中组部后台）；地方遴选偶有萝卜岗；遴选分数构成：笔试40%+面试30%+差额考察30%；5年服务期内不得参加遴选。",
        "importance": "high",
        "common_misconception": "以为遴选都是内定、考上基层再遴选很容易。",
        "actionable_advice": "入职第一天就为遴选做准备日常工作就是遴选题库；争取年度考核优秀；优先报中央/省级遴选。",
        "verification_method": "查阅公务员公开遴选办法；找到历年遴选真题了解考试方向。",
        "tags": ["遴选", "晋升", "中央遴选"],
        "sort_order": 24,
    },
    {
        "stage": "career_dev",
        "category": "晋升真相",
        "title": "职务职级并行不是到点就提",
        "content": "公务员实行职务+职级双轨制，职级并行解决待遇问题但不解决权力问题；基层职级有比例限制不是满年限就自动晋升；两办组织部等核心部门晋升速度是清水衙门的2-3倍；写材料能力是普通人最可复制的核心竞争力。",
        "importance": "high",
        "common_misconception": "以为职级并行就是熬年限、干得好就一定能提。",
        "actionable_advice": "若在基层提前了解单位职级空缺情况；苦练写材料能力这是最快脱颖而出的路径。",
        "verification_method": "查看单位近3年职级晋升公示名单和任职年限；咨询中层干部的晋升耗时。",
        "tags": ["晋升", "职级并行", "写材料"],
        "sort_order": 25,
    },
    {
        "stage": "career_dev",
        "category": "产品工具",
        "title": "公考雷达有用但VIP不值，粉笔足够备考",
        "content": "公考雷达免费版足够用于岗位筛选，VIP预测报名人数和预估进面分不准确；粉笔980系统班+刷题足够笔试备考；三大机构共同问题是只解决怎么考不解决考哪里，缺乏体制内真实生态、部门差异、待遇细节。",
        "importance": "medium",
        "common_misconception": "完全依赖公考雷达选岗、认为VIP预测分数很准、报保过班。",
        "actionable_advice": "免费版雷达+粉笔980足够；选岗和职业规划不要听培训机构的（他们希望你年年考）。",
        "verification_method": "用雷达数据和官方公布的最终报名人数/进面分数线对比验证。",
        "tags": ["公考雷达", "粉笔", "培训机构", "选岗"],
        "sort_order": 26,
    },
    {
        "stage": "career_dev",
        "category": "市场产品空白",
        "title": "市面公考产品五大信息空白",
        "content": "当前公考产品几乎都未覆盖：①真实待遇数据（全包收入构成、各部门年终系数）；②岗位真实工作状态（加班强度、核心工作内容）；③入职后生存指南（试用期、借调、晋升、调动潜规则）；④政审/体检的具体淘汰案例和标准细节；⑤体制内职业长期规划。这些信息目前只能通过在职人员口口相传获取。",
        "importance": "high",
        "common_misconception": "以为培训机构掌握所有内部信息。",
        "actionable_advice": "建立自己的信息渠道——QZZN论坛、小红书/知乎在职人员经验贴、体制内熟人网络；多个信息源交叉验证。",
        "verification_method": "对关键信息至少找3个独立来源验证。",
        "tags": ["信息差", "QZZN", "论坛", "交叉验证"],
        "sort_order": 27,
    },
    {
        "stage": "career_dev",
        "category": "长期规划",
        "title": "考公不是终点：入职后的职业规划更重要",
        "content": "考上公务员只是开始不是终点：入职后需要规划是走遴选向上流动、在原单位深耕晋升、还是发展副业（合规范围内）；体制内同样需要持续学习和能力建设，写材料、协调沟通、业务能力是核心竞争力；不要以为上岸就可以躺平。",
        "importance": "high",
        "common_misconception": "以为考上公务员就一劳永逸可以躺平了。",
        "actionable_advice": "入职前3年打好基础（写材料+业务能力+人脉）；明确自己的发展方向（技术型/管理型/遴选型）；保持学习习惯。",
        "verification_method": "观察单位内不同年龄段同事的状态和发展路径；找到自己的职业榜样。",
        "tags": ["职业规划", "入职后", "发展", "写材料"],
        "sort_order": 28,
    },
]

# 阶段名称映射
STAGE_NAMES = {
    "early_prep": "大一准备",
    "preparation": "备考选岗",
    "exam": "笔试面试",
    "onboarding": "入职适应",
    "career_dev": "职业发展",
}


# ===== 暗知识服务 =====

def seed_civil_service_dark_knowledge(db: Session) -> int:
    """如果暗知识表为空，预填充种子数据。返回填充条数。"""
    existing = db.query(CivilServiceDarkKnowledge).count()
    if existing > 0:
        return 0
    for item in CIVIL_SERVICE_DARK_KNOWLEDGE_SEED:
        db.add(CivilServiceDarkKnowledge(**item))
    db.commit()
    return len(CIVIL_SERVICE_DARK_KNOWLEDGE_SEED)


def get_civil_service_dark_knowledge_by_stage(db: Session, stage: str | None = None) -> list[CivilServiceDarkKnowledge]:
    """按阶段获取暗知识列表。"""
    query = db.query(CivilServiceDarkKnowledge)
    if stage:
        query = query.filter(CivilServiceDarkKnowledge.stage == stage)
    return query.order_by(CivilServiceDarkKnowledge.sort_order).all()


def get_civil_service_dark_knowledge_stages(db: Session) -> list[dict]:
    """获取各阶段的统计信息。"""
    results = []
    for stage_code, stage_name in STAGE_NAMES.items():
        count = db.query(CivilServiceDarkKnowledge).filter(
            CivilServiceDarkKnowledge.stage == stage_code
        ).count()
        results.append({
            "stage": stage_code,
            "stage_name": stage_name,
            "count": count,
        })
    return results


# ===== 岗位情报服务 =====

async def query_post_intel(region: str, department: str, post_name: str, exam_type: str) -> dict:
    """AI 查询岗位情报。不落库，返回结构化结果供前端预览。"""
    system_prompt = """你是一位资深体制内情报分析师，专门分析中国公务员/事业单位岗位的真实情况和信息差。

用户会提供地区、部门、岗位名称和考试类型，你需要输出结构化的岗位情报。

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "region": "地区",
  "department": "部门",
  "post_name": "岗位名称",
  "exam_type": "考试类型",
  "real_competition": "low/medium/high/extreme/unknown",
  "treatment_level": "low/medium/high/top/unknown",
  "promotion_speed": "slow/medium/fast/unknown",
  "workload": "light/moderate/heavy/extreme/unknown",
  "radish_post": "unlikely/possible/likely/unknown",
  "service_period": "yes/no/unknown",
  "admission_ratio": "预估报录比，如 25:1",
  "cutoff_score": 预估进面分数线（整数，如135）,
  "salary_estimate": "年薪估算描述，如 到手12-15万/年",
  "housing_fund": "公积金描述，如 双边2000/月",
  "bonus_info": "年终绩效描述",
  "department_tier": "部门梯队描述，如 第一梯队（两办组纪宣）",
  "work_content": "核心工作内容描述",
  "insider_notes": "内部消息和注意事项，如 加班强度、科室氛围、领导风格等",
  "risk_warnings": ["风险提示列表，每条一句话"],
  "data_sources": ["数据来源说明，如 QZZN论坛、在职人员反馈、公开招录数据等"],
  "tags": ["标签列表，如 国考、税务、热门岗、应届生友好"],
  "ai_summary": "100-200字的综合分析总结"
}
```

枚举值说明：
- real_competition: low=竞争小(20:1以内), medium=中等(20-50:1), high=激烈(50-200:1), extreme=极其激烈(200:1以上)
- treatment_level: low=6-10万/年, medium=10-18万/年, high=18-30万/年, top=30万+/年
- promotion_speed: slow=晋升慢（清水衙门）, medium=中等, fast=晋升快（核心部门）
- workload: light=清闲, moderate=适中, heavy=较忙, extreme=极忙（两办/纪委常加班）
- radish_post: unlikely=不太可能, possible=有可能, likely=很可能是萝卜岗
- service_period: yes=有5年服务期, no=无明确服务期, unknown=不确定

重要：不确定的信息一律标为 unknown 或 null，不要编造。所有判断都要基于公开可查的信息和体制内常识。"""

    user_content = f"地区：{region}\n部门：{department}\n岗位：{post_name}\n考试类型：{exam_type}\n\n请提供这个岗位的真实情报。"

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_content, timeout=45)

    # 提取 JSON
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                data = json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                match2 = re.search(r"\{.*\}", raw, re.DOTALL)
                if match2:
                    try:
                        data = json.loads(match2.group(0))
                    except (json.JSONDecodeError, TypeError):
                        data = {}
                else:
                    data = {}
        else:
            data = {}

    # 确保必要字段存在
    data.setdefault("region", region)
    data.setdefault("department", department)
    data.setdefault("post_name", post_name)
    data.setdefault("exam_type", exam_type)
    data.setdefault("real_competition", "unknown")
    data.setdefault("treatment_level", "unknown")
    data.setdefault("promotion_speed", "unknown")
    data.setdefault("workload", "unknown")
    data.setdefault("radish_post", "unknown")
    data.setdefault("service_period", "unknown")
    data.setdefault("admission_ratio", None)
    data.setdefault("cutoff_score", None)
    data.setdefault("salary_estimate", None)
    data.setdefault("housing_fund", None)
    data.setdefault("bonus_info", None)
    data.setdefault("department_tier", None)
    data.setdefault("work_content", None)
    data.setdefault("insider_notes", None)
    data.setdefault("risk_warnings", [])
    data.setdefault("data_sources", [])
    data.setdefault("tags", [])
    data.setdefault("ai_summary", "")

    return data


def save_post_intel(db: Session, user_id: UUID, data: dict) -> PostIntel:
    """保存岗位情报。"""
    intel = PostIntel(user_id=user_id, **data)
    db.add(intel)
    db.commit()
    db.refresh(intel)
    return intel


def get_user_post_intel_list(db: Session, user_id: UUID) -> list[PostIntel]:
    return (
        db.query(PostIntel)
        .filter(PostIntel.user_id == user_id)
        .order_by(PostIntel.created_at.desc())
        .all()
    )


def delete_post_intel(db: Session, user_id: UUID, intel_id: UUID) -> bool:
    intel = (
        db.query(PostIntel)
        .filter(PostIntel.id == intel_id, PostIntel.user_id == user_id)
        .first()
    )
    if not intel:
        return False
    db.delete(intel)
    db.commit()
    return True


# ===== 考公定位服务 =====

async def create_civil_service_positioning(db: Session, user_id: UUID, data: dict) -> CivilServicePositioning:
    """创建考公定位，自动触发 AI 评估。"""
    positioning = CivilServicePositioning(user_id=user_id, **data)
    db.add(positioning)
    db.commit()
    db.refresh(positioning)

    # AI 生成评估
    try:
        ai_result = await _generate_civil_service_assessment(positioning)
        positioning.ai_assessment = ai_result.get("ai_assessment", "")
        positioning.competitiveness_score = ai_result.get("competitiveness_score")
        positioning.eligible_for_xuandiao = ai_result.get("eligible_for_xuandiao", False)
        positioning.reach_posts = ai_result.get("reach_posts", [])
        positioning.target_posts = ai_result.get("target_posts", [])
        positioning.safety_posts = ai_result.get("safety_posts", [])
        positioning.preparation_timeline = ai_result.get("preparation_timeline", "")
        positioning.risk_warnings = ai_result.get("risk_warnings", [])
        db.commit()
        db.refresh(positioning)
    except Exception:
        positioning.ai_assessment = "AI 评估暂时不可用，请稍后重试。"
        db.commit()
        db.refresh(positioning)

    return positioning


async def _generate_civil_service_assessment(positioning: CivilServicePositioning) -> dict:
    """AI 生成考公定位评估。"""
    system_prompt = """你是一位资深考公规划师和体制内过来人，深谙中国公务员考试的信息不对称和选岗策略。

用户会提供个人背景信息，你需要：
1. 评估其考公竞争力（0-100分）
2. 判断是否符合选调生条件
3. 推荐三档目标岗位：冲刺（20-40%概率）、匹配（50-70%概率）、保底（80-95%概率），每档3-5个岗位
4. 制定备考时间线
5. 给出风险提示

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "ai_assessment": "300-500字的综合评估，包括竞争力分析、选岗方向建议、核心优势与劣势、赛道选择建议",
  "competitiveness_score": 0到100的整数,
  "eligible_for_xuandiao": true或false,
  "reach_posts": [
    {"region": "地区", "department": "部门", "post": "具体岗位", "reason": "推荐理由", "probability": 30}
  ],
  "target_posts": [
    {"region": "地区", "department": "部门", "post": "具体岗位", "reason": "推荐理由", "probability": 60}
  ],
  "safety_posts": [
    {"region": "地区", "department": "部门", "post": "具体岗位", "reason": "推荐理由", "probability": 90}
  ],
  "preparation_timeline": "备考时间线安排建议，分阶段描述",
  "risk_warnings": ["风险提示列表，每条一句话"]
}
```

每档推荐3-5个岗位。岗位要具体到部门和岗位类型（如 国家税务总局XX市税务局-一级行政执法员）。
选岗建议需考虑：专业匹配度、应届生身份、政治面貌、学历层次、目标地区待遇水平、竞争激烈程度。
不确定的评分给中间值，不要给极端值。"""

    party_status = "是" if positioning.is_party_member else "否"
    leader_status = "是" if positioning.student_leader else "否"
    honors_status = "是" if positioning.has_honors else "否"
    fresh_status = "是" if positioning.is_fresh_graduate else "否"

    user_content = f"""个人背景：
学历层次：{positioning.education_level}
学校层次：{positioning.school_tier or '未提供'}
专业：{positioning.major or '未提供'}
是否党员：{party_status}
是否学生干部：{leader_status}
是否有校级以上荣誉：{honors_status}
是否应届生：{fresh_status}
目标地区：{positioning.target_region or '未提供'}
目标考试类型：{positioning.target_type or '未提供'}
家庭背景：{positioning.family_background or '未提供'}
其他信息：{positioning.other_info or '无'}
"""

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(system_prompt=system_prompt, user_prompt=user_content, timeout=45)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                data = json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                match2 = re.search(r"\{.*\}", raw, re.DOTALL)
                if match2:
                    try:
                        data = json.loads(match2.group(0))
                    except (json.JSONDecodeError, TypeError):
                        data = {}
                else:
                    data = {}
        else:
            data = {}

    data.setdefault("ai_assessment", "")
    data.setdefault("competitiveness_score", 50)
    data.setdefault("eligible_for_xuandiao", False)
    data.setdefault("reach_posts", [])
    data.setdefault("target_posts", [])
    data.setdefault("safety_posts", [])
    data.setdefault("preparation_timeline", "")
    data.setdefault("risk_warnings", [])

    return data


def get_latest_civil_service_positioning(db: Session, user_id: UUID) -> CivilServicePositioning | None:
    return (
        db.query(CivilServicePositioning)
        .filter(CivilServicePositioning.user_id == user_id)
        .order_by(CivilServicePositioning.created_at.desc())
        .first()
    )


def get_civil_service_positioning_history(db: Session, user_id: UUID) -> list[CivilServicePositioning]:
    return (
        db.query(CivilServicePositioning)
        .filter(CivilServicePositioning.user_id == user_id)
        .order_by(CivilServicePositioning.created_at.desc())
        .all()
    )