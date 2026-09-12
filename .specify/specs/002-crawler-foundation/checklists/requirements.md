# Specification Quality Checklist: 爬虫地基（002）

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-12
**Feature**: [.specify/specs/002-crawler-foundation/spec.md](../spec.md)

## Content Quality

- [x] 需求面向机制与结果（护栏生效/死线必被知/加线机械化），不是流水账实现步骤（实现落点在 plan.md）
- [x] 聚焦真实痛点：本特性用户=加线的开发者/维护者/数据消费者/审计者（US1-US4）
- [x] 全部强制节完成（Overview/对账/US/红线/FR/排除/Acceptance/Notes）

## Requirement Completeness

- [x] 无 [NEEDS CLARIFICATION] 残留（歧义由 09-06 四份实测文档+当日侦察消解；假设入 §8 A1-A5）
- [x] 每条 FR 可测试（FR8 直接映射四判据测试名）
- [x] 验收可度量（四判据+全量绿+四闸+冒烟）
- [x] 边界情形已识别（A4 误杀 call site/A6 隔离误伤/A3 双库迁移/A10 假绿）
- [x] 范围清晰（§6 不做清单显式排除真实新线/yanzhao 数据/gwy 处置/dk 读路径）
- [x] 依赖与假设成文（蓝图文档链+宪法 8 条+R1-R6 红线）

## Feature Readiness

- [x] 每个 FR 有验收路径（FR1 守卫测试、FR2 契约测试、FR3/4/5 各自负例、FR6 演练测试、FR7 删后 collect+grep 双证）
- [x] 用户场景覆盖主流程（改版爆炸/死线告警/无证据拒收/加线 30 分钟）
- [x] 满足 Success Criteria（spec §7 五条）

## Notes

- 本特性属内部工程地基，"technology-agnostic"按房屋惯例放宽到「不引新框架」这一条硬约束（宪法+蓝图裁决：APScheduler+httpx 够用十年）。
- 宪法 8 条逐条过筛：零造假→R1/FR4；定位红线→R3/§6；合规爬取→R2/FR1；时间诚实→不涉及新文案；身份覆盖→不涉及；推送纪律→不涉及；工程纪律→A2/A3/验收5；部署纪律→R5/验收5。
