# Feature Spec 001：考公流程时间线伴随 MVP（Phase 1）

- **Branch**: deploy-rebased（生产权威链由 gp-converge 收敛，不建 speckit 特性分支）
- **Created**: 2026-09-12 ｜ **窗口**: 9/13–9/22 ｜ **依据**: `delivery/GradPath计划书-信息差伴随层-2026-09-12.md` v0.2；口号=已拍板 B「替你盯信息差，准时推你一把」
- **Input**: 用户 09-12 指令链（战略转向 → 计划书 → 职位 UI 下架 → 要求 speckit 详细计划）

## 1. Overview

把"考公 12 环节"做成一条带官方来源的权威时间线：用户订阅某场考试后，GradPath 在每个节点准时提醒"该做什么+官方入口直链+材料清单"，并承接完成回传（北极星"条件完成率+回传率"的天然数据源）。不承载报名动作本身——把人准时送到正确的官方网页面，这就是"信息差伴随层"的脊柱。

## 2. User Stories

- **US1（未登录可见）**：访客打开考公中心"考试流程"tab，能看到国考 2027 骨架：12 环节顺序、固定官方入口、已知 OFFICIAL 节点与 PREDICTED 节点（带"预测"标签），全部可点开来源。
- **US2（订阅+提醒）**：登录用户订阅"国考 2027"→ 节点到达提醒窗口时收到站内 Notification(type=reminder) + Server 酱推送，文案含该节点的动作指引与官方直链。
- **US3（回传）**：用户在节点卡上点"已完成/未完成/不确定"，写回订阅记录，喂条件完成率。
- **US4（2026 全周期范本）**：国考 2026 已完成周期全部节点为 OFFICIAL+带源，可作对照学习；同场考试"暗知识"卡按 stage 挂到对应节点。
- **US5（负例护栏）**：不存在任何路径让 PREDICTED 日期产生断言式提醒文案；被预测节点的公告一旦被人工/Phase 2 捕获为 OFFICIAL，旧预测文案不残留。

## 2.5 证据链硬闸（09-12 用户质询"seed 是不是假数据"后新增，优先级高于一切交付速度）

**背景实证（同日探针）**：www.scs.gov.cn 返回 985B 跳转壳、bm.scs.gov.cn 返回 4276B SPA 壳——正文抓不到；gov.cn 检索未命中公告静态原文；生产库 official_announce 归口只覆盖考研院校页，考公情报表 0 行。**即：系统当前不存在任何可自动验证的 2026 国考日期来源。** 因此：

- **FR-E1** 任何 `date_status=OFFICIAL` 的节点写入必须通过 seed/服务的 `require_evidence()` 闸，三条件缺一不可：① seed 运行时对 source_url 真实 HTTP 请求=200 且正文 ≥2KB（排除 SPA 壳）；② 抓取正文文本包含所写日期字符串（归一化比对）；③ 证据行入库（source_url、fetched_at、content_sha、命中段落 excerpt、渠道∈{fetch, manual_paste}）。
- **FR-E2** `manual_paste` 渠道：用户/运营粘贴官方公告原文 + 官方域名 URL，脚本校验"粘贴文本含日期"后落 OFFICIAL，evidence 标 manual_paste+粘贴人+时间，全文留档可审计。
- **FR-E3** seed 脚本内置常量**只允许** stage_key/标题/材料清单/官方入口 URL 骨架；**所有日期字段零默认值**。凭模型记忆手填日期 = 构造上不可能。
- **FR-E4** 取不到证据的节点（含 2026 的某些环节）保持 PREDICTED/UNKNOWN，UI 显示"暂无可核验来源"——宁可页面看起来"没数据"，不伪装知道。
- **FR-E5** 负例：喂"无证据的日期"给 seed → 拒绝；喂 <2KB 壳页 → 闸拒；闸测试进 CI 级脚本清单（quickstart §1/§3）。
- **FR-E6（09-12 二次修订新增）** 预测锚点链：2027 节点可为 `PREDICTED` 的唯一条件是 `predict_basis` 指向 **2026 同环节的证据行（evidence_id 存在）**；2026 无证据 ⇒ 2027 对应节点一律 `UNKNOWN`。禁止以"业内都知道 10 月中旬发公告"这类未落证的共识作推算依据——推算的推算还是编造。

| # | 要求 | 优先级 |
|---|---|---|
| FR1 | 实体：Exam（考次）/ ExamNode（12 环节节点，含 date_status ∈ {OFFICIAL, PREDICTED, UNKNOWN}、planned_date 可空、official_entry_url、source_url、materials、node_seq）/ ExamSubscription（用户×考次，唯一）/ NodeFeedback（订阅×节点，done/skipped/uncertain+时间） | P0 |
| FR2 | 节点提醒 job：进程内 APScheduler 日扫（复用 `_register_d2_reminder_job` 启动注册先例），按节点提前量表（公告日 T-3/T-1、报名 开始日、截止 T-1、缴费 T-1、准考证日、笔试日、查分开、面试/体检/政审按卡）生成提醒；幂等唯一键 (user, node, reminder_kind) | P0 |
| FR3 | 文案分级闸：reminder_kind 为断言类（"明天截止"等）时校验 `date_status==OFFICIAL`，否则只允许试探类模板；此闸有负例测试且测试断言打到最终文案（宪法 4） | P0 |
| FR4 | 推送配额：INFO 类并入现"≤3 条/天"限流口径；断言类节点提醒属重要级不受 INFO 限，但同一节点同一 kind 终身一条（幂等键） | P0 |
| FR5 | API 契约见 `contracts/timeline-api.md`；浏览公开、订阅/回传登录态（get_current_user） | P0 |
| FR6 | 前端：考公中心新增"考试流程"tab（垂直时间轴+下一节点高亮+订阅按钮+材料清单+官方直链+预测标签），不动现有 /timeline（个人行动线，语义不同） | P0 |
| FR7 | 数据入库：国考 2026 节点**仅在有证据链（FR-E1/E2）处写 OFFICIAL，否则保持 PREDICTED/UNKNOWN**；2027 骨架（入口 URL 有源；日期一律 PREDICTED/UNKNOWN）；省考广东 2026 同规则 | P0（12 环节骨架+2027 为最小集，2026 事实按证据到位进度） |
| FR8 | 北极星口径：条件完成率=Σdone 节点/Σ已到达窗口节点；回传率=有反馈回应的提醒/发出提醒——定义写进 `docs/度量口径.md` 增补节 | P1 |
| FR9 | 与暗知识 stage 词表建立映射列（node.stage_key ↔ CivilServiceDarkKnowledge.stage），命中则节点卡渲染经验卡（带三级可信度标注） | P1 |
| FR10 | Phase 2 预留：节点保留 `official_announce_id` 可空外键位（或 JSON 留痕），公告捕获后 OFFICIAL 覆写 PREDICTED 并推"时间已官宣" | P2（本期仅留字段，不做捕获） |

## 4. 范围排除（不做清单）

职位表解析/入库；考研/就业线复制（Q5）；经验讨论源爬取（Q3 公告日后再开）；报名人数动态（外链）；把决策引擎从辅助升回主打；自动化抓取公告（属 Phase 2）；`/timeline` 页改造。

## 5. Acceptance（与计划书一致 + 宪法级负例）

1. E2E：注册测试号→订阅国考 2027→时间调至某 OFFICIAL 节点前 1 天→跑 job→站内通知+Server 酱实收（服务器侧实证）；PREDICTED 节点同日跑→只出试探文案。
2. 时间线页数据：抽查 10 节点 100% 带源或带显式状态标签；预测标签肉眼可见。
3. 回传闭环：done 回传落库、北极星 SQL 可查询出数。
4. 三绿 + gp-preflight 四闸 + 生产 HTTPS 冒烟；冒烟账号删除。
5. 负例测试在 CI/本地全绿（FR3 闸），且测试名可追溯到宪法 4。

## 6. Notes / Assumptions

- A1：2026 国考日期**不预设能拿到**。取源顺序：①找政府域静态原文页（新华/人民网转登的公告全文，URL 须 gov.cn 域）供 fetch 证据闸；②找不到→向用户要公告原文粘贴（manual_paste 通道）。两条都断则 2026 相关节点以 PREDICTED 展示。**任何情况下不由模型记忆直接落库**（本条即 09-12 质询后的修订，取代旧"人工标定"笼统表述）。
- A2：Server 酱通道沿用现网配置（.env 已具备）；推送失败仅告警不阻塞（push_notify 现行语义）。
- A3：提醒扫描日任务成本可忽略（订阅数×几十节点）。
