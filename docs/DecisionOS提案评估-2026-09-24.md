# Decision OS 范式重构提案评估（2026-09-24）

> **【执行终态 2026-09-25】**：用户已拍板「开」（grilling 十问全按推荐，Q2 改立即开工，冻结窗豁免+010 观察 UI 零改动两前提留痕于下一阶段计划 D9 行）。本文§一-§五的评估结论已被执行覆盖：Phase 1+2 全链上产（域模型五表+17 API+证据闸 internal_unverified→Provider Router 7 白名单→外部验证 SSRF 闸/冲突不覆盖→首页决策卡+导航→工作台双面板；终版 145adfb，生产冒烟 9/9 绿）。**本文以下内容转为历史评估存档**，现役真相 = 仓库 CONTEXT.md + ADR-004 + 记忆 decision-os-proposal-d9 文件；遗留（工作台 UX 打磨/010 T2 待 AI 恢复）见记忆。
>
> 产出：调控席（方向/规格席位）。性质 = 决策收件箱 D9 的拍板支撑材料，**非 spec、非开工计划**。
> 触发：用户 09-24 二十节指令全文（把 GradPath 重构为"大学生重大决策验证系统 / Decision OS"）。
> 处置依据：`docs/需求冻结窗-2026-09-19.md`（窗内不拍板新方向、新想法只登记）。本文 = 把指令从"冲动"翻译成"10/2 可拍的事实"。
> 数据日期：2026-09-24，基于 deploy-rebased 工作区 HEAD 7172c52 只读审计（含 Explore 子代理全库实读，证据为 file:line）。

## 一、先纠偏：指令的现状声称 vs 实测

指令称"现有系统已具备 Hypothesis、Evidence、Prediction、Outcome、Reflection"。实测：**这五个作为决策域实体全部不存在**。全库 `hypothesis` 前后端 0 命中；`prediction` 只是 `destination_decisions.prediction` 自由文本字段（`models/destination_decision.py:43`）；唯一 Evidence 实体 `t_timeline_evidence` 属考试时间线域（`models/exam_timeline.py:120`）。

指令"严格禁止"清单里的大部分坏事，实测**并没有发生**：
- "AI 自动选 Winner"——`winner` 是加权矩阵算术 max（`decision_analysis_service.py:42`），三路引擎纯规则且文案明确"不替用户决定"（`path_decision_engine.py:4,1429`）；decision_advice 输出结构无 winner 字段。
- "虚假预测准确率"——`prediction_match/accuracy_score` 只存在于 `decision_review.py:70` 的注释里，无任何实际写入路径，未落库。
- "数据库里有就自动 VERIFIED"——不存在自动验证逻辑；唯一 `is_verified` 在 `experience_post`（人工语义）。

结论：**指令的差距判断建立在想象现状上；真实差距 = 七个一等实体从零建 + 三套孤立行动系统挂接，是重写级工程，不是改造级。**

## 二、七实体映射表（提案概念 → 实测现状 → 差距）

| 提案实体 | 实测现状 | 差距性质 | 量级 |
|---|---|---|---|
| Decision | `DestinationDecision`（destination_type 枚举 + prediction/assumptions JSONB/review 日志字段） | 半成品：缺 options/constraints/desired_outcome 结构化；question 语义弱 | 中 |
| Hypothesis | 无。最接近物 = `assumptions` JSONB 字符串数组 | **从零建**（含 importance/confidence/status/impact 状态机） | 大 |
| Evidence | 决策域无；`t_timeline_evidence` + `timeline_service.require_evidence()` 写入门控 = 同构先例可借鉴 | 从零建（claim/source/reliability/stance/verification_status） | 大 |
| Action | 三套并存互不连通：`micro_action_plans/tasks`（无决策 FK）、`t_action.source_decision_id`（裸 BigInteger 无 FK，模型自述"仅落库建表实现延后"）、`actions.py` 契约表 | 整合+挂接，不是新建 | 中 |
| Prediction | 自由文本字段 | 从零结构化（metric/target/probability/horizon/success_condition） | 中 |
| Outcome | `outcome_reports` 孤表（仅 user_id FK），语义是"上岸结果回传" | 挂接 decision FK + 支持 direct/partial/unobservable 四态 | 中 |
| Reflection | `retrospectives` 孤表（周期复盘语义）+ `decision_review_queue`（有 prediction vs actual 回顾流程 = 雏形） | 挂接 + 补 `ai_review_result` 实际写入路径 | 中 |

Evidence Provider 侧：数据溯源字段参差——school/company **完全无 source 字段**；grad/civil 情报有 `data_sources` JSONB + `verification_method`；experience_post 有三件套。Provider 化的前置 = 先补齐溯源，否则"internal_unverified"分级无从谈起。

## 三、可复用资产（提案不必从白纸开始）

1. **去推荐化已完成一半**：winner 本就是算术展示、引擎文案已拒绝替用户决定；剩余动作只是把 `winner/recommendation` 字段标记 legacy。
2. **Evidence Gate 有同构先例**：时间线域 `require_evidence()`（唯一写入口+官方域名校验+_fetch_log 留痕）就是 Evidence Gate 的模式样板，可直接平移语义。
3. **decision_journal 的 prediction vs actual 回顾流程** = Reflection 的产品雏形，缺的只是结构化落库。
4. **决策复盘队列 + UserMemoryFact**（decision_pulse 已消费）= Personal Decision Memory 的已有底座。
5. **005 伴随面板的"两段先行垂直切片"方法论**：若 10/2 拍板做，应复用此方法论压缩为"最小 Decision OS"（一条决策从创建→假设→证据→行动→复盘走通的垂直切片），而非按十阶段平铺。

## 四、与 010（访谈驱动伴随）的关系——不是纯互斥，是承接关系

010 的判定逻辑原文（09-19 拍板）："缺口 = **结构化台账 × 决策流程**，非'记得你'"。Decision OS 恰好是这个缺口的完整答案。因此：

- 若 10/2 复盘 010 T2 **打平**（ChatGPT 开记忆跑同款访谈不输站上）→ 产品按 010 预案降级收尾，Decision OS 作为收尾形态的"结构化决策台账"继承者，反而成立。
- 若 010 **成立** → 访谈成为 Decision 的自然语言输入端（指令第九节的"自然语言→AI 结构化→用户确认"与访谈驱动天然同构），Decision OS 是其远期形态。
- 两种结局下 Decision OS 都有位置，但**都不能推翻"先小切口验证、再平台化"的次序**——这正是 09-19 冻结窗要治的"建的速度>定的速度"。

## 五、拍板建议（10/2 复盘用）

1. **不建议**按十阶段平铺执行（单人+多会话节奏下重演"沉慢乱"的概率高）。
2. **建议**若拍板采纳，压缩为三步垂直切片：①域模型+孤表挂接（Outcome/Reflection/MicroAction 挂 decision FK，Hypothesis/Evidence/Prediction 新建）→ ②Action-Hypothesis 闭环（复用 decision_journal 流程）→ ③决策首页（复用 005 面板模式）。Phase 3 外部验证/Provider Router 延后到切片验证后。
3. **前置条件**：010 T2 结果先出（10/2 前）；数据资产溯源补齐（school/company）可与 004 情报流搭车。
4. 北极星衔接：Outcome 回传率 = 现有回传率的深化；Decision-Linked Action = 条件完成率的升级口径——不需要新北极星。

## 六、三点纪律冲突（留痕）

① 撞冻结窗"不拍板新方向"（窗 9/23-10/2，本文产出日 09-24 在窗内，故只评估不开工）；② 与 010"禁止扩散"的表面冲突已在上节重新解释为承接关系，但次序不可倒置；③ 指令现状声称与实测大面积不符，后续若再收到类似长指令，先过"快照必须现场复测"闸再动。

## 七、09-24 追问补充：两者能否并行（用户问"不能一起做吗"）

结论：**能共存于一个产品，不能并行开工为两个本体**。010 拍板原文的赌注="缺口=结构化台账×决策流程，非'记得你'"，而 Decision OS 恰是该赌注的完整形态——两者是同一条赌注的上下游，不是两个方向。合并形态=一条管线：

访谈（010，输入端）→ 原则库+结构化为 Decision/Hypotheses（D9 最小台账，存储端）→ 证据/行动/预测/复盘闭环（D9，处理端）→ 原则库注入对话（010 已有 user_context 机制，回流端）。该管线中访谈=Decision 的创建流程，台账=访谈的沉淀物，无主从之分。

真正冲突收窄为三处，均有解：

1. **叙事唯一性**：两个"产品本体"并存=缝合怪复发（09-19 自诊断原病）。解=拍板一次合成上述单管线，对外只讲一个故事。
2. **实验有效性**：T2b 对照组+30 天自发第三次访谈都要求产品面稳定；十阶段重构首页/决策页=观察期内换产品面，"自发使用"信号作废（"禁止扩散"的实际含义）。解=若坚持并行，只做完全不动 UI 的后端最小台账，访谈流程一字不改。
3. **次序与容量**：冻结窗 004+005 在飞，重写级工程挤入=沉慢乱复发；且 T2b 若打平，"用户要 AI 伴随处理决策"前提未验证，台账有建成无源之水的风险。解=10/2 拍板形态定为**"访谈驱动的 Decision OS"**，Phase 1=访谈产出直接写入决策台账的最小垂直切片（010 打平→台账按预案降级后仍是继承者；成立→台账是其远期形态，两态皆兼容）。

并行开工的两前提（若用户坚持现在做）：①冻结窗对新工豁免的拍板留痕；②承诺 010 观察 UI 面零改动。缺一不动工。
