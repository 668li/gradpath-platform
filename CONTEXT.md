# CONTEXT.md — GradPath 领域术语表

> 唯一术语真相源。改术语先改这里；实现细节不进本文件。
> 建立：2026-09-25（D9 拍板「开」：访谈驱动的 Decision OS 单管线）。

## 决策域

### Decision（决策）
用户正在面对的一个真实重大选择（如"要不要跨专业考研"）。不是"职业规划"，也不是一次问答。
- 用一句中性的疑问句表述（question），不预设答案。
- 状态推进由用户确认，系统不替用户选。

### Hypothesis（关键假设）
"如果这个判断不成立，我的 Decision 就不成立"的可证伪命题。
- 必须能被证据支持或反驳；写不出反例的不是假设。
- 与"原则"严格区分，不互转。

### 原则（Principle）
用户从访谈/复盘中沉淀的经验法则。不可证伪、不挂证据，用途是注入对话。
- 来源：访谈产出、从被证伪假设提炼的教训。
- 与 Hypothesis 的区别：原则是"我怎么判断"，假设是"什么必须为真"。

### DecisionEvidence（决策证据）
一条有来源、立场、可靠性的主张（claim），可被验证、冲突或过期。
- 叫 DecisionEvidence 不叫 Evidence：Evidence 一词已被考试时间线域占用（公告快照语义）。
- 任何证据创建即 internal_unverified。

### internal_unverified（内部未验证）
内部数据库产出的证据的默认状态。"库里有这条数据"永远不等于"这条数据已验证"。
- 只有带 verification_source 的显式验证动作才能改变它。
- 外部来源与内部来源冲突时两者都保留（contradicted），不覆盖。

### Evidence Provider（证据提供方）
内部数据库或外部源。只产出候选证据，永远不产出真相。
- 内部表是 Provider，不是真相源；provider 名只是出处的标注。

### ValidationAction（验证行动）
为降低某个 Hypothesis 的不确定性而设计的最小真实行动（如"采访 3 名跨考上岸学生"）。
- 必须能回答：验证哪个假设？降低哪种不确定性？结果可能改变什么？
- 不是日常打卡任务；与既有三套行动系统语义不同。

### DecisionOutcome（决策结果）
一个决策在现实中产生的反馈。允许四种形态：
direct（直接可见）/ partial（部分可见）/ unobservable（不可观测）/ counterfactual_unknown（反事实不可知）。
- 不强迫所有结果变成"成功/失败"。

### Reflection（复盘）
对照预期与结果的结构化记录：预测误差、错误假设、遗漏因素、教训。
- 产出可沉淀为新的"原则"。

### Personal Decision Memory（个人决策记忆）
用户所有 Decision Trace 的积累（决策→假设→证据→行动→结果→复盘）。
- 不是"AI 记得用户"；是用户自己可回看的决策史。

## 展示与 AI 纪律

### 不替用户决定（No Winner）
矩阵、加权、AI 分析只呈现权衡、敏感性与信息缺口；不输出"你应该选 A"。
- legacy：decision_analyses.winner / recommendation 字段保留仅作历史展示，新逻辑不得依赖。

### 最小验证（Minimum Verification）
每个假设优先设计成本最低、信息量最大的行动，而不是先收集更多信息。
