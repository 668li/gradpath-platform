# ADR-004: Decision OS 扩展 destination_decisions，不新建第二张决策表

- 状态：已采纳（2026-09-25，D9 拍板「开」时 grilling Q5）
- 关联：docs/DecisionOS提案评估-2026-09-24.md、CONTEXT.md、迁移 e9c2a7d4f1b3

## 背景

Decision OS 需要 Decision 作为一等实体（question/context/options/constraints/desired_outcome
结构化 + 挂 Hypothesis/Evidence/Action/Outcome/Reflection）。09-24 指令原文建议
"新建 decisions 表 + legacy 双写逐步迁移"。实测审计结论：`DestinationDecision`
不是历史包袱而是半成品——已带 prediction/assumptions/review 日志字段，且
`decision_analyses.decision_id`、`decision_review_queue.decision_id` 等存量外键
都指向它。

## 决策

扩展 `destination_decisions`（迁移 e9c2a7d4f1b3 新增
question/context/constraints/options/desired_outcome 五列，全部可空或带默认、
零回填），五张新表挂其 id。**不新建第二张决策表。**

## 理由

1. 双决策表 = 双真相。本仓历史上"两套口径"反复出事（护城河审计、假数据事故），
   两张 Decision 表必然再次分叉。
2. 存量 FK 链（decision_analyses / decision_review_queue / 前端 4 个决策页）不动，
   兼容面最小。
3. 半成品补列的迁移成本远低于双写切换。

## 后果

- 表名 `destination_decisions` 与概念名 Decision 不一致——接受，代码注释与
  CONTEXT.md 已说明；对外 API 与 UI 一律叫"决策/Decision OS"。
- legacy 字段（`assumptions`/`prediction`）保留；新逻辑只读 `decision_hypotheses`；
  `confirm_draft` 把假设 statement 镜像进 `assumptions` 保旧视图可读（有注释标注）。
- `decision_analyses.winner`/`recommendation` 为 legacy 展示字段，新逻辑不得依赖
  （CONTEXT.md「不替用户决定」）。

## 翻转条件

若未来 Decision 出现根本不同的生命周期（如非"去向"类决策占主导、需要多态决策），
再评估抽表；路径 = 先双写 → 校验一致 → 切读 → 删旧列，禁止直接 reset。
