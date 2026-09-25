# Feature Spec 005：伴随面板（缺口漏斗 pull 版）

- **Branch**: deploy-rebased（生产权威链由 gp-converge 收敛，不建 speckit 特性分支）
- **Created**: 2026-09-14（规格席位）｜ **形态**: 考试流程 tab 内"我的伴跑"视图（不新建页面）
- **依据**: 09-14 拍板（B1 改写=pull 式缺口漏斗面板；B2 强化=敢说真话/可信/懂你；B3 提醒击毙→日历降级为面板基建）；`docs/综合调研v2-第一性原理与对抗审查-2026-09-14.md`（L2 节点驱动密度 / L4 冷启动两问 / L5 节点日历双轨）；`docs/下一阶段计划-2026-09-14.md` §三点五；`.specify/memory/constitution.md`
- **方法论**: spec-driven-development（本文件=Phase 1）+ planning-and-task-breakdown（plan.md=Phase 2/3，垂直切片）

## 1. Overview

**产品定义**：行动层 = 调度器，不是记录本。面板回答三个问题，全部在打开站点那一刻交付（全 pull）：
1. **我到哪一步了** —— 当前节点（时间线 next_node：标题、日期三态、行动指引、官方入口）；
2. **我卡在哪** —— 条件账本缺口（未满足项分硬门槛/可补项，各带行动建议；空账本时诚实空态）；
3. **本站盯到了什么增量** —— 对我订阅的考次，本站捕获的事件/情报卡增量（带来源角标）。

**为什么是 pull**：推送/提醒差异化已于 09-14 击毙（公考雷达免费覆盖+个人无服务号权限）。本面板零渠道依赖，价值在"打开即见我的状态"，不在"第 N 层推送"。

**节点驱动密度（L2）**：面板信息密度随节点临近升档（远期周更语义/临近节点日更语义），不做每日必推的假日常感；事件型流程按事件密度呈现。

## 2. User Stories

- **US1（伴跑两段）**：已选目标考次的用户打开考公中心→考试流程 tab，首屏见"我的伴跑"：当前节点 + 我的缺口，无需订阅、无需填表。
- **US2（缺口联动）**：缺口段数据=条件账本结算（硬门槛未满足/可补项+行动建议，纯规则零 LLM）；未核对过任何目标时显示引导（"先完成考公定位/选目标，缺口将在这里出现"），不造假缺口。
- **US3（增量+来源角标）**：增量段=004 事件流∩我订阅的考次，每条带来源（官方域名链接+可信度标签+采集时间）；无增量时诚实空态（"本站在盯 N 个源，暂无新发布"）。
- **US4（冷启动两问）**：无目标/无订阅用户，面板仍产出（只有节点线；缺口与增量段给引导空态）；两问起步（身份+目标），账本靠动作副产品逐步填充。
- **US5（诚实三态）**：节点日期沿用 OFFICIAL/PREDICTED/UNKNOWN 三态展示与文案分级（PREDICTED 不出现断言式措辞）；面板不产生任何无来源的"事实"。

## 3. 功能需求

| # | 要求 | 优先级 |
|---|---|---|
| FR1 | **伴跑聚合端点** `GET /api/civil-service/timeline/me/companion`（登录）：一次返回三段结构（next_node / gaps / intel_feed），每段带显式状态（`ready` / `empty_reason`），零 LLM 零新表（实时聚合，不重复存事件） | P0 |
| FR2 | **缺口聚合（读，不新建数据）**：内部复用 `settle_checklist`（`/api/condition-checklist/my-profile-summary` 同源）——硬门槛/可补项+行动建议；无目标时 `empty_reason=no_target` | P0 |
| FR3 | **增量段**（依赖 004）：订阅考次的事件/情报卡增量，字段=title/source_url/fetched_at/credibility；无事件时 `empty_reason=no_event`；**004 未落地时该段恒为诚实空态，不阻塞 FR1/FR2/FR4** | P0（004 交付后为 P0，之前为 P1） |
| FR4 | **前端面板**（新组件 `components/civil-service/companion-panel.tsx`，挂进考试流程 tab 顶部）：三段卡片 + 来源角标 + 跳转（节点深链 C7、官方入口）；375px 可用 | P0 |
| FR5 | **节点深链联调**：本面板当前节点与 003 行动钩子深链（`/civil-service?tab=timeline&node=...` 形态）互通，同源锚点 | P1 |
| FR6 | **空态与引导**：no_target / no_event / not_subscribed 各有文案；全部为空时面板显示"备考全景"引导（两问起步） | P0 |
| FR7 | **来源角标统一形态**：增量与节点来源均显示"域名+可信度+时间"，复用 node 现有 `ShieldCheck` 样式；PREDICTED 用琥珀色+"预计" | P1 |

**不做（重申）**：不做推送/提醒渠道（09-14 拍板）；不做 ML 预测；不做聚合搜索入口；不新建独立页面（形态=B4 收敛：并入考试流程 tab）；不复制职位库/报录比。

## 4. 数据契约（三段结构草稿，执行期以代码为准）

```jsonc
{
  "next_node": {            // 可为 null（考次未就绪时）
    "exam_code": "gd_province_2026",
    "title": "报名", "seq": 3,
    "planned_date": "2026-01-08", "planned_end_date": null,
    "date_status": "PREDICTED",   // OFFICIAL | PREDICTED | UNKNOWN
    "action_guide": "...",
    "official_entry_url": "https://...",
    "source_url": null,           // OFFICIAL 时必有
    "deep_link": "/civil-service?tab=timeline&node=..."
  },
  "gaps": {
    "state": "ready",            // ready | empty_reason
    "empty_reason": null,        // no_target | no_checklist
    "completion_rate": 0.6,      // 与 /me completion_rate 同口径（北极星分母只算人工核对）
    "hard_gate_unmet": [ {"key": "...", "label": "...", "hint": "..."} ],
    "fixable_unmet": [ {"key": "...", "label": "...", "hint": "..."} ]
  },
  "intel_feed": {
    "state": "empty_reason",
    "empty_reason": "no_event",  // not_subscribed | no_event | source_pending(004未落地)
    "watched_sources": 3,        // 本站在盯的源数（诚实展示，非造假）
    "items": [ {"title": "...", "source_url": "...", "fetched_at": "...", "credibility": "OFFICIAL"} ]
  }
}
```

## 5. 验收（详见 quickstart.md）

1. 本地：两段先行（FR1/FR2/FR4/FR6）全链演练——登录→面板三段状态正确→空态文案正确；断网/无目标时无误报。
2. 负例：无目标不造缺口；未订阅不造增量；PREDICTED 节点不出现断言式文案（穿展示层）。
3. 部署后 HTTPS 冒烟：登录态面板可见、来源可点、含本面板特有断言（如 `companion` 段状态字段与预期一致）。
4. 004 落地后：增量段接入事件流，`watched_sources` 与事件条数实测对账。

## 6. 依赖与前置

- **B4/B5 拍板**：面板形态与 skill 收敛口径（本 spec 按 B4"并入考试流程 tab"既定方向编写；B4 若改为删模拟器只留时间线，本 spec 不变）。
- **A 类批次 commit 后实施**（~~在途冲突面~~ 已于 09-15 19:2x 复测刷新，见 §6.1）。
- **004 交付**：仅影响 FR3（增量段）；FR1/FR2/FR4/FR6 可先行（垂直切片两段上线）。

### 6.1 实施窗口（09-15 19:2x 复测，HEAD `3473177`）

- **A1–A7 已 commit**（提交日 09-14 21:51 起）：`82535db`(A3) → `7816ebc`(A2) → `f9c997c`/`e34a228`(A4 暗知识全链下线) → `c1c7875`(A5/A6/A7) → `e57387a`(A4 补) → `af32d02`；其后 **09-15 19:01/19:12 又落两笔**：`8f320a5`(a4-residue 摘除暗知识唯一落表通道) + `3473177`(台账销账，HEAD)。**005 的实施前置已满足**（规格落盘于 09-14 20:59，当时判定为"在途"的三批随后均已落地）。
- ️ **SHA 会分钟级失效**：本条只是"窗口已开"的证据，开工时不要照抄 SHA，**按 `git log --oneline -8` 现场复核**（教训：09-14 深夜二测的"A4 待 commit/A5-A8 未开工"在 1.5 小时内即被推翻）。
- **残留 A 项**：**A8**（/admin 隐藏验证——`admin/layout.tsx` 已在，待三处实测）、**A9**（"备考工具" tab 语义待拍板：删 or 更名）。**A9 会改 `civil-service/page.tsx`**，与本面板同文件 → 实施前先看 A9 是否已拍板落地。
- **实测未变（已提交历史）**：`exam-timeline.tsx` 末次**提交**仍是 `f82aa44`(001 M4)——A 类**已提交批次**并未改它；`civil-service/page.tsx:274` 的 timeline tab 挂载点健在；`condition_checklist` / `exam_timeline` / `timeline_service` 在 A 类全部已提交批次中零改动。
- **⚠️ 但工作区已变（09-15 19:2x 当场发现）**：`frontend/components/civil-service/exam-timeline.tsx` **已进入在途修改**——摘除节点卡里的 `n.dark_knowledge` 渲染块（**-9 行，A4 暗知识残留收尾**，与已提交的 `8f320a5` a4-residue 同一条线）。同批在途另有 `types/index.ts`(-75 行，删 7 个 `DarkKnowledge*` 接口)、`kaoyan/compare`(-21)、`search`、`war-room`、`lib/api/grad.ts`(-1)、三份 docs、`n8n/SETUP.md`。
  - **对 005 的含义**：① 这不是 005 实施（同一条 A4 收尾线），**无人在抢做伴跑面板**；② 但 `exam-timeline.tsx` 正是 T4 的挂载文件 → **T4 必须等这笔记完再动**；③ 005 目标类型面 `frontend/types/exam-timeline.ts` **干净未被动**（对方动的是 `types/index.ts`），T3 不受影响。
- **纪律（B 计划）**：本条快照同样会失效——**开工第一步永远是现场 `git log --oneline -8` + `git status`**，不以本文档为准。

## 7. 既有资产复用（09-15 19:2x 实测——规划期漏项，实施必须复用）

001 已交付"流程伴随官"，本面板是同一批问题的面板形态。**以下资产已存在，T1/T2 不得另写**：

| 资产 | 位置 | 005 用途 |
|---|---|---|
| `_pick_timeline_exam(db, track)` | `services/data_search_service.py:348` | T1 考次选择（upcoming 优先否则取首）——直接把 T1 的"默认考次"规则从草稿变成复用 |
| `timeline_service`（`list_exams` / `get_my_exams` / `get_node_payload`） | `services/timeline_service.py` | T1 节点与进度解析 |
| `_status_label(date_status, planned_date)` | `skills/timeline_companion.py:173` | 三态文案**单点真源**：OFFICIAL→`官方：{date}`；PREDICTED→`预计 {date}，公告后自动更新`；UNKNOWN→`日期待定（暂无可核验来源）` |
| `ASSERTIVE_WORDS` | `services/timeline_reminder.py:48` | **N3 的现成实现**（"明天/今天/已发布/截止/已开启/取消/还有/现在开始"）——负例断言复用此词表，不自造 |
| `timeline_companion` skill 本身 | `skills/timeline_companion.py` | 语义参照：聊天侧与面板侧对同样三问**必须同口径**（面板若与聊天答案不一致即口径漂移） |

**由此收紧两条契约**：
1. 节点文案 = `_status_label` 产物，前端不自行拼接日期措辞 → N3 在数据源头即被闸住，展示层断言只是二次确认。
2. `next_node.date_label` 建议直接进契约（替代前端 dateLabel 重算），字段名执行期以代码为准并回填 §4。

## 8. 假设（错了现在纠正）

1. "我的伴跑"入口=考试流程 tab 顶部（不新建页、不进主导航）。
2. 增量段只显示**已订阅考次**的事件（未订阅不显示，避免"窥屏"感）；`watched_sources` 展示本站监控源总数。
3. `my-profile-summary` 的缺口语义可直接复用（其基于"最近核对目标职位"）；不新增条件类型。
4. completion_rate 沿用既有口径（done/已到窗口，分母只算人工核对），不另立指标。
5. 面板不引入新依赖、不做动画特效；375px 与桌面同为可读。
