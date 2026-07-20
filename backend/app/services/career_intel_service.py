"""求职作战室服务层 — 公司情报 + 求职定位 + 求职暗知识。

借鉴 grad_intel_service 的三段式结构，覆盖求职全流程的信息差。
"""
import json
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_intel import CareerDarkKnowledge, CareerPositioning, CompanyIntel
from app.services.ai_orchestrator import AIOrchestrator


# ===== 求职暗知识种子数据 =====
CAREER_DARK_KNOWLEDGE_SEED = [
    # ===== 自我认知阶段 =====
    {
        "stage": "self_awareness",
        "category": "应届生身份",
        "title": "应届生身份是你最大的红利，只有一次",
        "content": "央企招聘应届生比例不低于75%，60%以上国考省考岗位仅限应届生。同单位应届岗32人竞争1岗，往届岗146人抢1岗。管培生计划、导师带教、专属晋升通道（3年主管5年经理）几乎只对应届生开放。社招进来就要直接干活，没有培养资源。多省政策将应届生身份认定延长至毕业年度内（无论是否签约缴社保），但一旦缴了社保就失去应届生身份。",
        "importance": "critical",
        "common_misconception": "很多人以为签了三方协议或找到了工作就不算应届生了，实际上关键看是否缴纳了社保。毕业年度内即使签约也仍算应届。",
        "actionable_advice": "能走校招千万别放弃。如果不确定是否要工作，可以先保留应届生身份，利用毕业年度内的政策窗口期。",
        "verification_method": "查看目标企业的校招页面是否标注「仅限应届生」，以及国考省考职位表中的「应届」筛选条件。",
        "tags": ["应届生", "校招", "央企", "公务员"],
        "sort_order": 1,
    },
    {
        "stage": "self_awareness",
        "category": "学历门槛",
        "title": "第一学历的隐形权重：985/211筛简历是真的",
        "content": "企业招聘分三档：985、211、普通本科。双非第一学历可能连面试机会都没有。表面招研究生，实际筛的是本科——最高学历是参考，第一学历是门槛。教育部多次严禁发布限定985/211字样的招聘信息，但隐形门槛仍难根除。这不是明文规定，而是HR筛选简历时的结构性偏好。",
        "importance": "critical",
        "common_misconception": "很多人以为考上研究生就能洗掉本科出身，实际上很多企业同时看第一学历和最高学历，本科双非在部分行业仍然吃亏。",
        "actionable_advice": "双非背景的同学：①用实习和项目经历对冲学历劣势；②选择对学历更包容的行业（如互联网技术岗）；③考虑考研提升第一学历；④内推比网申更能绕过学历初筛。",
        "verification_method": "在脉脉或看准网搜索目标公司的匿名评价，看是否有「卡第一学历」的讨论；问已入职的同校学长学姐。",
        "tags": ["学历歧视", "双非", "简历筛选"],
        "sort_order": 2,
    },
    {
        "stage": "self_awareness",
        "category": "方向选择",
        "title": "选行业比选公司重要，选赛道比选岗位重要",
        "content": "行业决定天花板，公司决定地板。一个朝阳行业的中等公司，往往好过夕阳行业的头部公司。AI、新能源、半导体等行业处于上升期，机会多、涨薪快；而教培、房地产、传统纸媒等衰退行业，即使头部公司也面临裁员风险。赛道选择错了，个人努力很难对抗行业大势。",
        "importance": "high",
        "common_misconception": "很多人只看公司名气和薪资数字，不看行业趋势。进了大厂但选了边缘业务线，裁员时第一批走人。",
        "actionable_advice": "投递前先研究行业：①看行业近年投融资数据和人才需求趋势；②看头部企业财报中的业务增长方向；③选有政策支持的赛道（如新质生产力相关）。",
        "verification_method": "查看国家统计局行业数据、猎聘/智联年度人才报告、目标公司近3年财报营收趋势。",
        "tags": ["行业选择", "赛道", "趋势"],
        "sort_order": 3,
    },
    {
        "stage": "self_awareness",
        "category": "实习认知",
        "title": "超八成大学生大一大二就开始实习了",
        "content": "超八成受访大学生大一大二就开始实习。大三暑假是黄金实习季，争取1-2段高质量对口实习，优先头部企业。暑期实习有转正机会，有些大厂暑期实习转正率高达60-70%。实习经历是简历的核心加分项，没有实习经历的应届生在秋招中严重劣势。",
        "importance": "high",
        "common_misconception": "很多人以为实习是大四的事，等到秋招才发现简历上只有课程项目，和有2-3段实习经历的同学差距巨大。",
        "actionable_advice": "大一试探性实习，大二大三冲头部企业实习。实习定薪资，经历定offer。优先有转正机会的暑期实习。",
        "verification_method": "查看目标公司的校园招聘页面是否有「暑期实习转正」计划；在牛客/实习僧搜索该公司的实习转正率讨论。",
        "tags": ["实习", "转正", "秋招"],
        "sort_order": 4,
    },

    # ===== 简历投递阶段 =====
    {
        "stage": "application",
        "category": "内推机制",
        "title": "内推简历通过率比网申高3-5倍",
        "content": "内推简历通过率比网申高3-5倍，大厂尤甚。但内推分强弱：强关系内推（学长学姐直接递简历给HR）成功率远高于弱关系（公开内推码）。微博、小红书上的内推码鱼龙混杂，部分内推码来自为完成KPI的员工，后续帮助意愿不强。校院系交流群、就业指导中心藏有竞争小、成功率高的内推名额。",
        "importance": "critical",
        "common_misconception": "很多人以为填个内推码就等于内推了，实际上公开内推码和网申几乎没区别。真正有效的内推是找人把简历直接递到用人部门。",
        "actionable_advice": "①优先找同校学长学姐内推；②参加企业宣讲会当面递简历；③在脉脉/牛客找在职员工帮忙内推；④内推后主动跟进进度。",
        "verification_method": "问内推人是否能查到简历流转状态；在牛客内推广场看该公司的内推响应速度。",
        "tags": ["内推", "网申", "简历"],
        "sort_order": 5,
    },
    {
        "stage": "application",
        "category": "简历优化",
        "title": "简历被ATS系统筛选，关键词不匹配直接被淘汰",
        "content": "大部分中大型企业使用ATS（Applicant Tracking System）自动筛选简历。系统通过关键词匹配打分，低于阈值的简历HR根本看不到。JD中提到的技能、工具、经验如果不在简历中出现，匹配度就会很低。一份简历投所有岗位是最常见的错误。",
        "importance": "high",
        "common_misconception": "很多人以为简历写得越详细越好，实际上ATS更看重关键词匹配度。堆砌无关经历反而降低匹配分。",
        "actionable_advice": "①每个岗位定制简历，把JD中的关键词自然融入经历描述；②用数据量化成果（如「提升转化率15%」）；③技术岗把技能关键词放在显眼位置。",
        "verification_method": "用AI简历工具（如AI简历姬）模拟ATS打分；对比JD关键词和简历内容的匹配度。",
        "tags": ["简历", "ATS", "关键词"],
        "sort_order": 6,
    },
    {
        "stage": "application",
        "category": "岗位陷阱",
        "title": "招聘写「运营」实际做「销售」，岗位偷换很常见",
        "content": "68%求职者表示企业在招聘时存在美化行为。常见套路：招「运营」实际做销售轮岗打杂；写「扁平化管理」实际管理混乱；承诺「快速成长」实际无培养体系；写「弹性作息不内卷」实际大小周、996、无偿加班。岗位不真实是应届生最容易踩的坑。",
        "importance": "high",
        "common_misconception": "很多人以为招聘JD上写的就是实际工作内容，实际上JD是理想化的岗位描述，入职后可能完全不同。",
        "actionable_advice": "①面试时问「这个岗位每天具体做什么」「团队有几个人」「汇报线是怎样的」；②面试前在看准网/脉脉查公司真实评价；③入职前要求写明岗位职责的书面文件。",
        "verification_method": "在脉脉匿名区搜索公司名+「坑」「真实」等关键词；看准网查看该岗位的员工评价。",
        "tags": ["岗位陷阱", "JD美化", "销售转岗"],
        "sort_order": 7,
    },
    {
        "stage": "application",
        "category": "萝卜坑",
        "title": "有些岗位是「萝卜坑」，挂出来但已经内定了",
        "content": "央企核心岗位名额常被定向培养班、行业强校毕业生、内部子弟提前锁定。挂出的岗位条件苛刻到「量身定制」（如特定学校+特定专业+特定证书+特定年龄），普通学生连网申入口都找不到。这种情况在国企、事业单位尤其常见。",
        "importance": "high",
        "common_misconception": "很多人以为招聘条件越具体越精准，实际上是「萝卜坑」的概率越大。条件越奇葩、越像为某个人定制的，越要警惕。",
        "actionable_advice": "①看到条件极其具体且小众的岗位，大概率是萝卜坑，不要浪费时间；②优先投递条件宽泛、招聘人数多的岗位；③关注企业官网而非只看招聘平台。",
        "verification_method": "看该岗位是否只有1个名额且条件极其具体；搜索该单位是否有近期内部调动或定向培养信息。",
        "tags": ["萝卜坑", "央企", "内部子弟"],
        "sort_order": 8,
    },

    # ===== 面试阶段 =====
    {
        "stage": "interview",
        "category": "面试准备",
        "title": "87%应届生缺乏系统面试训练，初面淘汰率75%",
        "content": "87%应届生缺乏系统性面试训练，初面淘汰率高达75%，其中60%源于无法有效展示核心竞争力。面试不是聊天，是一场有结构的展示。STAR法则（情境-任务-行动-结果）是最基础的表达框架，但很多人连自己的项目经历都讲不清楚。",
        "importance": "high",
        "common_misconception": "很多人以为面试就是聊天，靠临场发挥。实际上面试官每个问题都有考察目的，没有准备的回答很难拿到高分。",
        "actionable_advice": "①用STAR法则准备3-5个项目故事；②提前研究公司面试题（牛客面经区）；③找朋友做模拟面试；④准备「你有什么问题想问我们」的提问。",
        "verification_method": "在牛客/看准网搜索目标公司的面经，看面试题型和考察维度。",
        "tags": ["面试", "STAR", "面经"],
        "sort_order": 9,
    },
    {
        "stage": "interview",
        "category": "面试信号",
        "title": "HR说「回去等通知」通常是婉拒",
        "content": "面试中有很多隐含信号：「回去等通知」通常是婉拒；「什么时候能入职」是积极信号；面试时间超过1小时说明聊得深入；面试官主动介绍团队和业务说明对你有兴趣。秋招岗位多规模大，春招偏向补招，需抢占秋招先机。",
        "importance": "medium",
        "common_misconception": "很多人以为「回去等通知」是真的在等流程，实际上面试官如果对你满意，通常会当场或很快给出下一轮安排。",
        "actionable_advice": "①面试结束问「大概什么时候能收到反馈」；②如果3-5个工作日没回复，主动跟进一次；③不要只等一家，多线并行。",
        "verification_method": "面试后记录面试官的措辞和态度，对比牛客面经区其他人的反馈时间。",
        "tags": ["面试信号", "HR", "婉拒"],
        "sort_order": 10,
    },
    {
        "stage": "interview",
        "category": "反向背调",
        "title": "面试是双向选择，你也要「反向背调」公司",
        "content": "00后求职已经开始反向背调公司——面试前查公司天眼查/企查查看经营状况、法律诉讼；看准网查员工真实评价；脉脉看匿名八卦；Glassdoor看面试体验。重点查：公司是否有劳动纠纷、是否欠薪、高管是否频繁变动、近半年是否有裁员记录。",
        "importance": "high",
        "common_misconception": "很多人只准备被面试，不准备面试公司。入职后发现公司有问题，已经浪费了应届生身份和时间。",
        "actionable_advice": "①天眼查看公司法律风险和经营异常；②看准网看员工评价中「缺点」部分；③脉脉搜公司名+「裁员」「加班」「拖欠」；④面试时问「团队最近半年人员流动情况」。",
        "verification_method": "天眼查/企查查看法律诉讼记录；看准网差评区；脉脉匿名区搜索公司名。",
        "tags": ["背调", "天眼查", "公司调研"],
        "sort_order": 11,
    },

    # ===== 签约阶段 =====
    {
        "stage": "signing",
        "category": "三方协议",
        "title": "三方协议违约金陷阱：高额违约金是「行业惯例」？",
        "content": "三方协议是学校、学生、企业三方签订的就业意向书，不是劳动合同。高额违约金常被解释为「行业惯例」，但法律上违约金应合理，过高可申请调整。企业可能扣押三方原件拖延解约。近四成学生无法准确区分三方协议与劳动合同的法律效力。三方协议违约不影响应届生身份，但可能影响学校就业率统计。",
        "importance": "critical",
        "common_misconception": "很多人以为签了三方就必须去，不去了要赔很多钱。实际上三方协议的约束力远低于劳动合同，违约金也有法律上限。",
        "actionable_advice": "①签约前仔细看违约金条款，超过一个月工资可协商；②不要签空白三方；③如果需要解约，走正规流程并保留证据；④三方不等于劳动合同，入职后仍需签正式劳动合同。",
        "verification_method": "咨询学校就业指导中心关于三方的政策；查看《劳动合同法》关于违约金的规定。",
        "tags": ["三方协议", "违约金", "签约"],
        "sort_order": 12,
    },
    {
        "stage": "signing",
        "category": "薪资谈判",
        "title": "薪资谈判：HR压价是常规操作，你的第一报价决定了锚点",
        "content": "HR谈薪时会锚定你的期望值，你的第一报价决定了谈判区间。不清楚市场行情价是最大劣势。工龄1-3年跳槽核心涨幅8%-20%，最优报价12%-15%。通用职能岗上限锁定15%。同岗位公积金基数差1000元是常事。薪资倒挂（新员工比老员工高）在国企和传统行业很常见。",
        "importance": "high",
        "common_misconception": "很多人怕报高了被淘汰，报低了又亏。实际上HR有一个预算区间，你的报价只要在区间内就有谈判空间。不了解行情报低了，入职后才发现同事比你高很多。",
        "actionable_advice": "①面试前在OfferShow/看准网/脉脉查同岗位薪资；②报价比心理预期高10-15%留谈判空间；③谈总包（基本工资+绩效+年终+期权）不只看月薪；④问清五险一金缴纳基数。",
        "verification_method": "OfferShow小程序查校招薪资；看准网查社招薪资；脉脉匿名区搜公司+「薪资」。",
        "tags": ["薪资谈判", "HR压价", "锚定效应"],
        "sort_order": 13,
    },
    {
        "stage": "signing",
        "category": "offer比较",
        "title": "比较offer不能只看月薪，要看总包和隐性成本",
        "content": "offer比较维度：薪资构成（基本+绩效+年终+期权）、五险一金基数（差1000/月=年差1.6万）、加班强度（996的1.5万不如965的1.2万）、通勤时间、平台价值（大厂背书vs小厂成长）、团队氛围、晋升通道。有的公司月薪高但基数按最低缴，实际到手和长期权益都吃亏。",
        "importance": "high",
        "common_misconception": "很多人只比月薪数字，忽略了五险一金基数、加班时长、年终奖等隐性成本。月薪1.5万996的实际时薪可能低于月薪1.2万965的。",
        "actionable_advice": "①算时薪：月薪/（每周工时*4.3）；②问清五险一金缴纳基数和比例；③问年终奖实际发放情况（不是HR说的「大概」）；④用牛客offer比较功能让社区投票。",
        "verification_method": "在脉脉/看准网查该公司的实际五险一金缴纳基数；问已入职的学长学姐实际到手薪资。",
        "tags": ["offer比较", "总包", "五险一金"],
        "sort_order": 14,
    },

    # ===== 入职阶段 =====
    {
        "stage": "onboarding",
        "category": "试用期",
        "title": "试用期被辞退：企业不能只凭「不合适」就辞退你",
        "content": "企业合法解除试用期须同时满足：①入职前有书面、公示的明确录用条件和考核标准；②能拿出充分证据证明不符合要求。仅凭口头「不合适」不合法。试用期超6个月（非国企大厂）明显压榨，大概率转正即裁员。真实案例：某旅行社招10名应届生，约定6个月试用期，4个多月后全部以「考核不达标」解聘。60%以上毕业生签约前从未主动查阅相关法律条款。",
        "importance": "critical",
        "common_misconception": "很多人以为试用期企业可以随意辞退，实际上法律规定企业必须证明你不符合录用条件，且录用条件必须是入职前书面告知的。",
        "actionable_advice": "①入职时要求书面录用条件和考核标准；②保留工作记录和沟通证据；③被辞退时要求企业出具书面辞退理由；④不合法辞退可申请劳动仲裁。",
        "verification_method": "查看《劳动合同法》第39条；保留入职时的岗位说明书和考核标准文件。",
        "tags": ["试用期", "辞退", "劳动法"],
        "sort_order": 15,
    },
    {
        "stage": "onboarding",
        "category": "竞业协议",
        "title": "竞业协议：无补偿金的竞业协议无效",
        "content": "合法竞业限制最长2年，且企业需按月支付竞业补偿金（通常不低于离职前12个月平均工资的30%），无补偿金的竞业协议无效。法律上竞业仅限高管、高级技术人员和其他负有保密义务的人员。但现实中「全员竞业」乱象严重：实习生、厨师也被要求签竞业，离职后不仅去不了同行，连供应商公司都去不了。风险有「时间滞后性」，签约时难以预判。",
        "importance": "critical",
        "common_misconception": "很多人签合同时不仔细看竞业条款，以为只有高管才需要签。实际上很多公司让所有人都签，而且条款极其宽泛。",
        "actionable_advice": "①签合同前仔细看竞业条款的范围和补偿金；②如果竞业范围过于宽泛或无补偿金，可以拒绝签署或要求修改；③离职时确认竞业协议是否启动；④被竞业限制期间每月确认收到补偿金。",
        "verification_method": "查看《劳动合同法》第23-24条；咨询劳动法专业律师。",
        "tags": ["竞业协议", "补偿金", "劳动法"],
        "sort_order": 16,
    },
    {
        "stage": "onboarding",
        "category": "社保公积金",
        "title": "社保公积金基数差1000，一年差1.6万",
        "content": "缴费基数关乎终身法定权益：养老金、医保报销、失业金、公积金都挂钩。同岗位公积金差1000元是常事（因入职时间不同起算基数不同）。真实算账：8000月薪，按最低基数6000、最低5%缴，月入账户600；按实际8000、顶格12%缴，月入账户1920，一年差近1.6万。按最低基数缴费，医保个人账户划入减少，大额医疗自付压力更大。多数应届生只看工资条数字，不知五险一金基数差距。",
        "importance": "critical",
        "common_misconception": "很多人以为所有公司都按实际工资缴五险一金，实际上很多中小公司按最低基数缴纳以节省成本。月薪1万的offer如果按最低基数缴，实际权益比月薪8千按顶格缴的差很多。",
        "actionable_advice": "①谈offer时问「五险一金按什么基数缴纳」；②入职第一个月查社保缴费记录确认基数；③公积金比例差异巨大（5%-12%），直接影响贷款额度；④如果公司按最低基数缴纳，要在offer比较中折算真实价值。",
        "verification_method": "入职后通过「社保查询」小程序查看实际缴费基数；对比offer时的薪资承诺。",
        "tags": ["社保", "公积金", "缴费基数"],
        "sort_order": 17,
    },
    {
        "stage": "onboarding",
        "category": "入职收费",
        "title": "入职前收费全部是骗局，正规企业不收任何费用",
        "content": "企业以任何名目在入职前收费——岗前培训费、体检费、工装费、押金、保证金——全部是骗局。正规企业不收任何入职费用。有的公司绑定高额岗前培训，承诺培训后入职但实际是培训机构招生收费。近四成学生将实习期等同于试用期，概念认知系统性缺失。",
        "importance": "critical",
        "common_misconception": "有些人以为入职培训收费是正常的，实际上《劳动合同法》第9条明确规定用人单位不得扣押身份证件、不得要求担保、不得以其他名义向劳动者收取财物。",
        "actionable_advice": "①任何要求入职前交钱的公司直接拒绝；②被收费后保留证据并报警/投诉劳动监察；③区分实习（学校安排/无正式劳动关系）和试用期（正式劳动关系）；④体检费通常由企业承担或报销。",
        "verification_method": "查看《劳动合同法》第9条；向当地劳动监察部门举报收费行为。",
        "tags": ["入职骗局", "收费", "劳动法"],
        "sort_order": 18,
    },
    {
        "stage": "onboarding",
        "category": "跳槽时机",
        "title": "首份工作至少2-3年，未满1.5年不建议跳槽",
        "content": "12-24个月是黄金跳槽期——够久能讲出成果、够短还没被舒适圈锁住。但首份工作建议至少2-3年，未满1.5年跳槽HR默认稳定性差。工龄1-3年是跳槽性价比最高阶段。过早跳槽会形成「跳槽频繁」标签，影响后续求职。",
        "importance": "medium",
        "common_misconception": "很多人觉得工资低就想跳，但如果没有拿得出手的成果，跳了也涨不了多少。HR看到1年内跳槽的简历会直接筛掉。",
        "actionable_advice": "①首份工作至少做满2年，积累可量化的成果；②跳槽前确保有1-2个能讲深度的项目；③12-24个月是最佳窗口；④跳槽涨幅低于15%不值得动。",
        "verification_method": "在脉脉/看准网看同岗位跳槽后的薪资涨幅数据；对比自己在当前公司的成长速度。",
        "tags": ["跳槽", "稳定性", "涨薪"],
        "sort_order": 19,
    },
    {
        "stage": "onboarding",
        "category": "劳动维权",
        "title": "超半数学生权益受损选择忍气吞声，不知如何维权",
        "content": "超半数学生权益受损选择「忍气吞声」或不知如何维权。近半数认为「用人单位不会违法」。60%以上毕业生签约前从未主动查阅相关法律条款。实际上劳动法对劳动者保护非常全面：不签合同可主张双倍工资、违法解除可要求赔偿金、拖欠工资可投诉劳动监察。",
        "importance": "high",
        "common_misconception": "很多人觉得和公司打官司成本太高、时间太长，实际上劳动仲裁是免费的，而且大部分案件3个月内结案。很多公司收到仲裁通知就会主动和解。",
        "actionable_advice": "①保留所有工作证据（打卡记录、工资条、沟通截图）；②遇侵权先协商，协商不成申请劳动仲裁（免费）；③仲裁不服可向法院起诉；④12333劳动保障热线可咨询举报。",
        "verification_method": "拨打12333劳动保障热线咨询；当地劳动人事争议仲裁委员会官网查询流程。",
        "tags": ["维权", "劳动仲裁", "12333"],
        "sort_order": 20,
    },
]

# 阶段名称映射
STAGE_NAMES = {
    "self_awareness": "自我认知",
    "application": "简历投递",
    "interview": "面试阶段",
    "signing": "签约阶段",
    "onboarding": "入职阶段",
}


# ===== 暗知识服务 =====

def seed_career_dark_knowledge(db: Session) -> int:
    """如果暗知识表为空，预填充种子数据。返回填充条数。"""
    existing = db.query(CareerDarkKnowledge).count()
    if existing > 0:
        return 0
    for item in CAREER_DARK_KNOWLEDGE_SEED:
        db.add(CareerDarkKnowledge(**item))
    db.commit()
    return len(CAREER_DARK_KNOWLEDGE_SEED)


def get_career_dark_knowledge_by_stage(
    db: Session,
    stage: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[CareerDarkKnowledge], int]:
    """按阶段获取暗知识列表，支持分页。"""
    query = db.query(CareerDarkKnowledge)
    if stage:
        query = query.filter(CareerDarkKnowledge.stage == stage)

    total = query.count()
    offset = (page - 1) * limit
    items = query.order_by(CareerDarkKnowledge.sort_order).offset(offset).limit(limit).all()

    return items, total


def get_career_dark_knowledge_stages(db: Session) -> list[dict]:
    """获取各阶段的统计信息。"""
    results = []
    for stage_code, stage_name in STAGE_NAMES.items():
        count = db.query(CareerDarkKnowledge).filter(
            CareerDarkKnowledge.stage == stage_code
        ).count()
        results.append({
            "stage": stage_code,
            "stage_name": stage_name,
            "count": count,
        })
    return results


# ===== 公司情报服务 =====

async def query_company_intel(company_name: str, position_name: str) -> dict:
    """AI 查询公司情报。不落库，返回结构化结果供前端预览。"""
    system_prompt = """你是一位资深职场情报分析师，专门分析中国企业的真实工作环境和招聘信息。

用户会提供公司名称和岗位名称，你需要输出结构化的公司情报。

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "company_name": "公司名称",
  "position_name": "岗位名称",
  "industry": "所属行业",
  "overtime_intensity": "none/mild/moderate/severe/unknown",
  "layoff_risk": "none/low/moderate/high/unknown",
  "promotion_outlook": "good/fair/poor/unknown",
  "education_barrier": "none/mild/moderate/severe/unknown",
  "salary_honesty": "honest/exaggerated/misleading/unknown",
  "culture_fit": "good/neutral/toxic/unknown",
  "salary_range": "该岗位的薪资范围描述，如 15-25k*16",
  "actual_salary": "实际到手薪资描述，注意绩效和年终的浮动",
  "interview_style": "面试风格描述，如 3轮：笔试+技术面+HR面，偏算法和系统设计",
  "interview_rounds": 面试轮数（整数）,
  "turnover_rate": "人员流动率描述，如 年流动率约15%",
  "growth_path": "晋升路径描述，如 初级-高级-专家-架构师，约3年一级",
  "insider_notes": "内部消息和注意事项，如 近期有裁员传闻、XX部门加班严重等",
  "risk_warnings": ["风险提示列表，每条一句话"],
  "data_sources": ["数据来源说明，如 看准网员工评价、脉脉匿名爆料、公开财报等"],
  "tags": ["标签列表，如 互联网、大厂、996、高薪"],
  "ai_summary": "100-200字的综合分析总结"
}
```

枚举值说明：
- overtime_intensity: none=不加班, mild=偶尔加班, moderate=经常加班, severe=严重加班/996
- layoff_risk: none=无风险, low=低风险, moderate=有风险, high=高风险
- promotion_outlook: good=晋升通畅, fair=一般, poor=晋升困难
- education_barrier: none=不卡学历, mild=轻微偏好, moderate=明显偏好, severe=严格卡学历
- salary_honesty: honest=薪资透明, exaggerated=部分夸大, misleading=严重误导
- culture_fit: good=氛围好, neutral=一般, toxic=氛围差

重要：不确定的信息一律标为 unknown 或 null，不要编造。所有判断都要基于公开可查的信息。"""

    user_content = f"公司：{company_name}\n岗位：{position_name}\n\n请提供这家公司这个岗位的真实情报。"

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
    data.setdefault("company_name", company_name)
    data.setdefault("position_name", position_name)
    data.setdefault("industry", "")
    data.setdefault("overtime_intensity", "unknown")
    data.setdefault("layoff_risk", "unknown")
    data.setdefault("promotion_outlook", "unknown")
    data.setdefault("education_barrier", "unknown")
    data.setdefault("salary_honesty", "unknown")
    data.setdefault("culture_fit", "unknown")
    data.setdefault("risk_warnings", [])
    data.setdefault("data_sources", [])
    data.setdefault("tags", [])
    data.setdefault("ai_summary", "")

    return data


def save_company_intel(db: Session, user_id: UUID, data: dict) -> CompanyIntel:
    """保存公司情报。"""
    intel = CompanyIntel(user_id=user_id, **data)
    db.add(intel)
    db.commit()
    db.refresh(intel)
    return intel


def get_user_company_intel_list(db: Session, user_id: UUID) -> list[CompanyIntel]:
    return (
        db.query(CompanyIntel)
        .filter(CompanyIntel.user_id == user_id)
        .order_by(CompanyIntel.created_at.desc())
        .all()
    )


def delete_company_intel(db: Session, user_id: UUID, intel_id: UUID) -> bool:
    intel = (
        db.query(CompanyIntel)
        .filter(CompanyIntel.id == intel_id, CompanyIntel.user_id == user_id)
        .first()
    )
    if not intel:
        return False
    db.delete(intel)
    db.commit()
    return True


# ===== 求职定位服务 =====

async def create_career_positioning(db: Session, user_id: UUID, data: dict) -> CareerPositioning:
    """创建求职定位，自动触发 AI 评估。"""
    positioning = CareerPositioning(user_id=user_id, **data)
    db.add(positioning)
    db.commit()
    db.refresh(positioning)

    # AI 生成评估
    try:
        ai_result = await _generate_career_assessment(positioning)
        positioning.ai_assessment = ai_result.get("ai_assessment", "")
        positioning.competitiveness_score = ai_result.get("competitiveness_score")
        positioning.reach_companies = ai_result.get("reach_companies", [])
        positioning.target_companies = ai_result.get("target_companies", [])
        positioning.safety_companies = ai_result.get("safety_companies", [])
        positioning.salary_estimate = ai_result.get("salary_estimate", "")
        positioning.skill_gaps = ai_result.get("skill_gaps", [])
        positioning.risk_warnings = ai_result.get("risk_warnings", [])
        db.commit()
        db.refresh(positioning)
    except Exception:
        positioning.ai_assessment = "AI 评估暂时不可用，请稍后重试。"
        db.commit()
        db.refresh(positioning)

    return positioning


async def _generate_career_assessment(positioning: CareerPositioning) -> dict:
    """AI 生成求职定位评估。"""
    system_prompt = """你是一位资深职业规划师和猎头顾问，深谙中国就业市场的信息不对称。

用户会提供个人背景信息，你需要：
1. 评估其在求职市场的竞争力（0-100分）
2. 推荐三档目标公司：冲刺（20-40%概率）、匹配（50-70%概率）、保底（80-95%概率）
3. 估算合理的薪资区间
4. 指出能力差距
5. 给出风险提示

严格输出以下 JSON 格式（不要输出任何其他内容）：
```json
{
  "ai_assessment": "300-500字的综合评估，包括竞争力分析、市场定位建议、核心优势与劣势",
  "competitiveness_score": 0到100的整数,
  "reach_companies": [
    {"name": "公司名", "position": "岗位", "tier": "公司层次如大厂/独角兽", "reason": "推荐理由", "probability": 30}
  ],
  "target_companies": [
    {"name": "公司名", "position": "岗位", "tier": "公司层次", "reason": "推荐理由", "probability": 60}
  ],
  "safety_companies": [
    {"name": "公司名", "position": "岗位", "tier": "公司层次", "reason": "推荐理由", "probability": 90}
  ],
  "salary_estimate": "如 15-22k*14-16薪",
  "skill_gaps": [
    {"skill": "缺失技能名", "importance": "critical/high/medium", "suggestion": "如何补齐的建议"}
  ],
  "risk_warnings": ["风险提示列表，每条一句话"]
}
```

每档推荐 3-5 家公司。公司名称要具体真实（如确实不了解可给行业典型公司名）。
不确定的评分给中间值，不要给极端值。"""

    user_content = f"""个人背景：
学历层次：{positioning.education_level}
学校层次：{positioning.school_tier or '未提供'}
专业：{positioning.major or '未提供'}
毕业年份：{positioning.graduation_year or '未提供'}
GPA：{positioning.gpa or '未提供'}
实习经历：{positioning.internships or '未提供'}
技能：{', '.join(positioning.skills) if positioning.skills else '未提供'}
竞赛获奖：{', '.join(positioning.competitions) if positioning.competitions else '未提供'}
项目经历：{positioning.projects or '未提供'}
证书：{positioning.certifications or '未提供'}
目标行业：{positioning.target_industry or '未提供'}
目标岗位：{positioning.target_position or '未提供'}
目标城市：{positioning.target_city or '未提供'}
期望薪资：{positioning.salary_expectation or '未提供'}
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
    data.setdefault("reach_companies", [])
    data.setdefault("target_companies", [])
    data.setdefault("safety_companies", [])
    data.setdefault("salary_estimate", "")
    data.setdefault("skill_gaps", [])
    data.setdefault("risk_warnings", [])

    return data


def get_latest_career_positioning(db: Session, user_id: UUID) -> CareerPositioning | None:
    return (
        db.query(CareerPositioning)
        .filter(CareerPositioning.user_id == user_id)
        .order_by(CareerPositioning.created_at.desc())
        .first()
    )


def get_career_positioning_history(db: Session, user_id: UUID) -> list[CareerPositioning]:
    return (
        db.query(CareerPositioning)
        .filter(CareerPositioning.user_id == user_id)
        .order_by(CareerPositioning.created_at.desc())
        .all()
    )
