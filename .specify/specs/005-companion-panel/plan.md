# Implementation Plan 005：伴随面板（缺口漏斗 pull 版）

> 方法论：planning-and-task-breakdown——垂直切片、依赖图、每任务显式验收+验证、检查点。
> 执行纪律：本 plan 的实施窗口 = **A 类批次 commit 之后**；**09-15 19:2x 复测：A1–A7 已 commit（HEAD `3473177`；开工时按 `git log --oneline -8` 现场复核，SHA 分钟级失效），窗口已开**（残留 A8/A9 见 spec §6.1）。两个会话共享工作区，实施前先 `tools/topology.sh` 对账。

## 1. Overview

在考试流程 tab 内交付"我的伴跑"面板，回答三问（我到哪一步/我卡在哪/本站盯到了什么增量），全 pull、零 LLM、零新表。**两段先行**（节点+缺口），增量段等 004。

## 2. Architecture Decisions

- **D0 复用 001 伴随官，不另写同义逻辑**（09-15 复测补入）：考次选择用 `data_search_service._pick_timeline_exam`（`:348`）、节点与进度用 `timeline_service`、三态文案用 `skills/timeline_companion._status_label`（`:173`）、断言词闸用 `timeline_reminder.ASSERTIVE_WORDS`（`:48`）。证据见 spec §7。**判定：本面板若自造日期文案或自造考次规则，即构成口径漂移（对应 §5 风险行）**。
- **D1 聚合在后端**：新端点 `GET /api/civil-service/timeline/me/companion`（挂 `exam_timeline.py` router，前缀实测=`/api/civil-service/timeline`，复用 `/me` 的登录依赖与考次解析），避免前端三次并发拆装与口径漂移；三段各自 `state/empty_reason`，前端只渲染。
- **D2 零新表**：只读聚合（timeline_service 现有查询 + `condition_checklist_service.settle_checklist`），不落库、不缓存（首版）。
- **D3 不重复存事件**：增量段直接读 004 的 ExamEvent/情报卡查询面（C1/C2 新建面），面板不建自己的事件表。
- **D4 复用既有前端范式**：新组件 `companion-panel.tsx` 挂 tab 顶部；不重构 `exam-timeline.tsx`（该文件 A 类**已提交批次**未改它，末次提交 `f82aa44`；但 **09-15 复测其工作区在途 -9 行** → T4 需等该笔记完，仍按最小侵入处理）；样式复用 STATUS_BADGE/dateLabel/ShieldCheck 现有形态（可 import 纯函数）。
- **D5 两段先行**：FR3 未就绪时 `intel_feed.state=empty_reason, empty_reason=source_pending`，面板不隐瞒（诚实空态）。
- **D6 与聊天侧同口径**：面板三问的答案须与 `timeline_companion` skill 的聊天答案一致；实现后做一次并排对账（同一考次同一节点，两侧文案/日期/状态应相同）。

## 3. Dependency Graph

```
[既有 001] _pick_timeline_exam / timeline_service / _status_label / ASSERTIVE_WORDS ─
[既有] /me（进度+completion_rate）──────────────────────────────────────────────────┤
[既有] condition_checklist.settle_checklist ────────────────────────────────────────┤
                                 ├─→ T1 后端伴跑端点 ─→ T2 后端契约测试 ─┐
[004] 事件流/情报卡查询面 ─────────（FR3，后置）                        │
                                                          T3 前端面板组件 ←┘
                                                                │
                                                          T4 tab 集成+空态
                                                                │
                                                    ┌──────────────────────┐
                                              T5 深度联调（深链/角标）  T6 增量段接入（004 后）
```

实施顺序自下而上：T1→T2→（检查点）→T3→T4→T5（检查点）→T6（004 后）。

## 4. Task List

### Phase 1 — 两段先行（后端）

- [ ] **T1 后端伴跑聚合端点**（M：3-5 文件）
  - Description：实现 `GET /api/civil-service/timeline/me/companion`，返回 next_node/gaps/intel_feed 三段结构（契约见 spec §4）；**考次选择必须调 `_pick_timeline_exam(db, track)`（已实测存在，`data_search_service.py:348`）**；next_node 复用 `timeline_service` 既有解析，文案走 `_status_label`（**不自行拼接日期措辞**，见 D0/D6）；gaps 读取 settle_checklist（state/empty_reason/completion_rate/hard_gate_unmet/fixable_unmet）；intel_feed 先固定 source_pending。
  - Acceptance：① 登录用户返回三段，字段与 spec §4 一致；② 无目标 → `gaps.empty_reason=no_target`；③ 无订阅 → `intel_feed.empty_reason=not_subscribed`；④ 未登录 401；⑤ **考次选择与聊天侧 `timeline_companion` 选中的同一考次一致**（同一输入下）。
  - Verify：`cd backend && py -3.13 -m pytest tests/test_companion_panel.py -q`；手工 curl 8001 三态。
  - Files：`backend/app/schemas/exam_timeline.py`（+CompanionVO）、`backend/app/api/exam_timeline.py`（+端点）、`backend/app/services/timeline_service.py`（+聚合函数，内部复用既有函数）、`backend/tests/test_companion_panel.py`（新）。
  - Deps：None（既有 001 资产已可用）。

- [ ] **T2 后端契约与负例测试**（S：1-2 文件）
  - Description：补齐 T1 的负例与边界——无目标不造假缺口、未订阅不造假增量、completion_rate 与 `/me` 同值对账、PREDICTED 节点进面板不产生断言式文案（**断言词表直接 import `timeline_reminder.ASSERTIVE_WORDS`（`:48`），不自造词表**，穿到序列化层断言）。
  - Acceptance：测试含至少 4 条负例断言，全绿；`require_evidence` 类闸门未被绕过（intel_feed 条目一律带 source_url）；**断言词检查与 `_status_label` 的 PREDICTED 产物兼容**（"预计 …，公告后自动更新" 不含 ASSERTIVE_WORDS 任一）。
  - Verify：同上 pytest 全量该文件；回归抽查 `tests/test_exam_timeline_api.py` 不红。
  - Files：`backend/tests/test_companion_panel.py`。
  - Deps：T1。

### Checkpoint A（T1-T2 后）
- [ ] 后端全绿（新文件 + 既有 exam-timeline 测试）；`import app.api.exam_timeline` 冒烟通过。
- [ ] 与执行会话确认：A 类批次已 commit（工作区无 staged 冲突）。

### Phase 2 — 面板（前端）

- [ ] **T3 前端伴跑面板组件**（M：2-4 文件）
  - Description：`companion-panel.tsx`——三段卡片：next_node（标题+dateLabel+STATUS_BADGE+行动指引+官方入口+深链按钮）、gaps（completion_rate 进度条+未满足清单分两组+行动建议）、intel_feed（条目带来源角标；空态三文案）。375px 可读。
  - Acceptance：① 三段各自 ready/empty 渲染正确；② 来源角标=域名+可信度+时间；③ PREDICTED 文案="预计 …"，无断言式；④ 无新依赖。
  - Verify：`cd frontend && npx tsc --noEmit`；vitest 对纯函数/渲染分支（如 dateLabel 复用已有测试）；手工 375px 截图。
  - Files：`frontend/components/civil-service/companion-panel.tsx`（新）、`frontend/lib/api/exam-timeline.ts`（+companion()）、`frontend/types/exam-timeline.ts`（+Companion 类型）。
  - Deps：T1。

- [ ] **T4 tab 集成与空态**（S：1-2 文件）
  - Description：`ExamTimelineTab` 顶部挂载面板（或 civil-service 页 timeline tab 内组合），空态/加载态与既有 LoadingState/EmptyState 一致；不改 timeline 主体逻辑（D4）。
  - Acceptance：① 打开考试流程 tab 即见面板（无需订阅）；② 冷启动两问引导可点进定位评估；③ 未登录时面板显示登录引导而非报错。
  - Verify：本地 dev 手测 + `npx tsc --noEmit` + vitest 不红。
  - Files：`frontend/components/civil-service/exam-timeline.tsx`（**仅顶部挂载，最小侵入**）、必要时 `page.tsx`。
  - Deps：T3。

### Checkpoint B（T3-T4 后）
- [ ] 前端三绿（lint/vitest/build）；面板在 375px 与桌面可读；无 A 类在途文件被本任务触碰（git status 核对）。
- [ ] 人工过目：三段语义与拍板口径一致（方向席位验收）。

### Phase 3 — 增量段接入（004 交付后）

- [ ] **T5 深度联调：深链与角标统一**（S：2-3 文件）
  - Description：面板节点与 003 行动钩子深链互通（`?tab=timeline&node=`）；intel_feed 与节点来源角标样式统一（同盾牌图标/域名格式）。
  - Acceptance：深链往返正确；角标样式一致；003 钩子曝光不被面板重复计数。
  - Verify：E2E/手测 + 埋点对账（若涉及）。
  - Files：`companion-panel.tsx`、`exam-timeline.tsx`（如需）。
  - Deps：T4。

- [ ] **T6 增量段接入 004 事件流**（M：2-4 文件）
  - Description：intel_feed 改为读 004 事件/情报卡查询面（订阅考次过滤），`watched_sources` 与源清单对账；SLA 展示字段（fetched_at）。
  - Acceptance：① 有事件时条目带完整来源字段；② `watched_sources`=当前监控源数（非造假）；③ 未订阅不显示条目；④ 004 负例（无证据）事件不出现。
  - Verify：本地全链演练（假源→事件→面板可见）；部署后 HTTPS 冒烟绑特有断言。
  - Files：`timeline_service.py`、`exam_timeline.py`、`companion-panel.tsx`、测试。
  - Deps：T4 + 004 交付。

### Checkpoint C（T5-T6 后）
- [ ] 004 数据到达时面板增量正确；SLA 字段与实测对账；回归全绿；部署冒烟通过。
- [ ] 方向席位验收通过后才算 005 完成。

## 5. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **自造同义逻辑致口径漂移**（规划期漏项，09-15 复测补入）：考次选择/三态文案/断言词闸在 001 已各有单点真源 | **高**：面板与聊天侧答案不一致、北极星口径被污染 | D0：复用 `_pick_timeline_exam` / `_status_label` / `ASSERTIVE_WORDS` / `timeline_service`，禁自造（spec §7 表）；D6 并排对账；T1 验收 ⑤ |
| 与并行会话在途文件冲突 | 高：卷入他人改动/半成品 | 09-15 19:2x 实测：A1–A7 已 commit；**⚠️ 但 `exam-timeline.tsx`（T4 挂载文件）当前在途 -9 行**（A4 暗知识残留收尾）→ **T4 等其 commit；T1/T2/T3 目标面干净可先行**；**另有 A9**（"备考工具" tab 待拍板，会改 `civil-service/page.tsx`，同文件）；开工前 `topology.sh` + `git status`（不以文档快照为准）；`exam-timeline.tsx` 仅顶部挂载不重构（D4） |
| `my-profile-summary` 基于"最近核对目标职位"（职位线已删，数据面收窄） | 中：缺口段多数用户 no_target | 空态引导两问起步（FR6）；不造假缺口；后续可评估把"考公定位评估"作为缺口源（二期） |
| 004 延期致增量段空置 | 低：面板仍有两段价值 | 两段先行（D5）+ source_pending 诚实空态 |
| completion_rate 口径漂移 | 中：北极星口径被污染 | 直接复用 `/me` 同源计算，不另立（假设 4） |
| 面板变"第 N 层提醒" | 中：违背拍板 | 全 pull、零推送渠道、无红点催促；PREDICTED 诚实文案 |

## 6. Checkpoints 汇总
- Checkpoint A：后端全绿 + import 冒烟 + 与执行会话对账。
- Checkpoint B：前端三绿 + 375px + 方向席位过目语义。
- Checkpoint C：004 数据接入 + 部署冒烟 + 方向席位验收。

## 7. Open Questions
- B4 拍板若改为"连模拟器都砍只留时间线"，本面板形态不变（已按收敛方向编写）——仅需确认。
- B5 skill 收敛是否搭车本 spec（需求建议：**不搭车**，避免范围膨胀；skill 收敛另立小任务）。
- 缺口段的"考公定位评估"能否成为第二缺口源（二期评估，非本期）。
