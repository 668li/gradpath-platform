# GradPath Decision Evidence Loop

## 本阶段目标

把现有 DestinationDecision.assumptions: list[str] 升级成可验证的数据链：

Decision → Hypothesis → Evidence → Action → Outcome

本次只落地前 3 层，不提前声称“决策正确率”。

## 数据契约

### DecisionHypothesis

- statement：假设是什么
- importance：1~5，越高越值得优先验证
- confidence：0~1，表示当前主观置信度，不是客观概率
- status：open / validated / invalidated / superseded
- verification_question：验证这个假设时真正要回答的问题
- validation_action：最小验证行动

### DecisionEvidence

- claim：具体声称什么
- source_type：official / dataset / peer / user / research / other
- reliability：1~5，来源可靠性
- stance：supports / refutes / neutral
- source_url + excerpt：保留溯源信息
- hypothesis_id：可选；没有假设时可以作为 decision-level evidence

## 为什么先做数据模型，而不是先做“决策评分”

没有真实 outcome 数据时，GradPath 不应该输出一个伪精确的“正确率”或“成功概率”。

第一阶段只衡量：

- 假设是否被提出
- 假设是否有证据
- 证据来自什么来源
- 证据是支持还是反驳
- 当前还有多少关键假设没有验证

这样 Decision Engine 可以先被验证为证据组织与验证系统，而不是未经校准的预测器。

## 后续 Evidence Provider

已有院校、分数线、薪资、公司/招聘、公考数据都作为 provider：

Decision → Evidence Gap → Provider Query → DecisionEvidence

provider 不需要一次性覆盖全站；只有当前决策产生具体证据缺口时才查询对应数据。

## 当前 API

- GET/POST /api/decisions/{decision_id}/hypotheses
- PATCH/DELETE /api/decisions/{decision_id}/hypotheses/{hypothesis_id}
- GET/POST /api/decisions/{decision_id}/evidence
- PATCH/DELETE /api/decisions/{decision_id}/evidence/{evidence_id}
- GET /api/decisions/{decision_id}/evidence-readiness

evidence-readiness 只返回证据覆盖度，不输出“你这个决定是对的”。

## 下一阶段

1. 把现有 assumptions 一键迁移成初始 Hypothesis。
2. 将现有院校/分数线/薪资/招聘/公考数据接成 Evidence Provider。
3. 将 MicroAction 与 hypothesis_id 绑定，形成验证行动。
4. 将 Outcome/Review 绑定到假设，形成预测误差/假设误差数据。