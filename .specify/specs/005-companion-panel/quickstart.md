# Quickstart & 验收 005：伴随面板（缺口漏斗 pull 版）

> 验收总纪律：`verify-gate-at-fact-moment-principle`（验收闸在事实产生刻）+ constitution 8 条 + `docs/验收清单-2026-09-14.md` 总则（执行会话交证据包五件，方向席位逐条实测复核）。

## §1 开工前置（实施第一步，单列）

1. **A 类批次已 commit**：**09-15 19:2x 复测已满足**——`git log --oneline -8` 应见 `3473177`(HEAD，09-15 19:12 台账) ← `8f320a5`(09-15 19:01 a4-residue) ← `af32d02` ← `e57387a` ← `c1c7875`(A5/A6/A7) ← `e34a228`/`f9c997c`(A4)；**SHA 分钟级失效，以现场 `git log` 为准**；`git status` 无他人 staged 冲突（共享工作区纪律）。**残留 A 项**：A8（/admin 隐藏验证，待三处实测）、**A9（"备考工具" tab 待拍板，会改 `civil-service/page.tsx`——本面板同文件，先确认其状态）**。
2. **topology 对账**：`bash tools/topology.sh`（三分支/生产线对账）。
3. **契约核对**：读 `.specify/specs/005-companion-panel/spec.md` §4 数据契约 + **§7 既有资产复用表** + `plan.md` §2 架构决策；以代码实际形状为准，发现漂移先回填 spec（命名漂移记录见 §5）。

## §2 本地实施与演练

```bash
# 后端（端口 8001；pytest 从 backend 目录跑）
cd backend && py -3.13 -m pytest tests/test_companion_panel.py -q
py -3.13 -c "import app.api.exam_timeline; print('IMPORT OK')"

# 前端（端口 3000）
cd frontend && npx tsc --noEmit && npx vitest run
```

**演练脚本**（T1/T4 完成后）：
1. 登录测试账号（邮箱须 example.com 域）→ 打开 `/civil-service?tab=timeline` → 面板三段落位；
2. 无目标态：`gaps.empty_reason=no_target` + 引导文案；
3. 无订阅态：`intel_feed.empty_reason=not_subscribed` + "本站在盯 N 个源"；
4. 断网/后端起不来：面板降级为加载失败文案，不白屏（前端容错）。

## §3 负例清单（防假绿，进 CI 级脚本）

| # | 负例 | 断言位置 |
|---|---|---|
| N1 | 无目标不造缺口 | 后端：`settle_checklist` 空时 `empty_reason=no_target`，`hard_gate_unmet=[]` |
| N2 | 未订阅不造增量 | 后端：无订阅时 `items=[]` 且 `empty_reason=not_subscribed` |
| N3 | PREDICTED 不产生断言式文案 | **穿到序列化/展示层**：含"预计"、"建议"，不含 `timeline_reminder.ASSERTIVE_WORDS`（`:48`，8 词）任一——**断言词表 import 复用，不自造** |
| N4 | 无来源不进增量 | 后端：intel_feed 条目 `source_url` 空则拒收（对齐 004 FR-E1b） |
| N5 | completion_rate 同源 | 面板值 == `/me` 同考次值（同一次请求内对账） |

## §4 部署与冒烟（HTTPS）

1. `gp-preflight.sh` 四闸 → bundle→scp→`update_from_bundle.sh`（沿用 gradpath-deploy skill）；
2. **冒烟绑定本面板特有断言**：登录态下 `GET /api/civil-service/timeline/me/companion` 返回三段且 `next_node.deep_link` 可解析；（不接受"页面能打开"）；
3. 冒烟账号验证后删除；更新后必部署才勾账。

## §5 命名漂移记录（执行时以代码为准，发现即回填）

- spec 称"考次详情 C2"等为 001 契约别名：实际端点见 `backend/app/api/exam_timeline.py`（`/exams/{code}`）；
- 缺口聚合实际函数：`condition_checklist_service.settle_checklist`（`/api/condition-checklist/my-profile-summary` 同源）；
- 进度/完成率实际字段：`MyExamItem.progress.reached/done` + `completion_rate`（本案不另立口径）；
- 事件/情报卡查询面 = 004 新建（C1/C2），名称以 004 交付代码为准。
- **既有 001 伴随官资产（09-14 实测，实施须复用而非另写——见 spec §7）**：
  - 考次选择 `data_search_service._pick_timeline_exam(db, track)`（`:348`，upcoming 优先否则取首）；
  - 三态文案 `skills/timeline_companion._status_label(date_status, planned_date)`（`:173`）——OFFICIAL→`官方：{date}`／PREDICTED→`预计 {date}，公告后自动更新`／UNKNOWN→`日期待定（暂无可核验来源）`；
  - 断言词闸 `services/timeline_reminder.ASSERTIVE_WORDS`（`:48`）；
  - **命名撞车提示**：仓库已有 `skills/timeline_companion.py` 与 `tests/test_timeline_companion.py`；本案新建的 `companion-panel.tsx` / `test_companion_panel.py` 与之**文件不冲突**，但语义相邻，注释与命名须能区分"聊天伴随官 vs 面板伴随"。**建议执行期把新测试命名统一为 `test_companion_panel.py`（勿用 `test_timeline_companion*`，避免与既有文件混淆）**。

## §6 验收清单（方向席位逐条实测）

| # | 检查点 | 判据 | 锚点（规划时点已实测） |
|---|---|---|---|
| 1 | 聚合端点存在且三段契约一致 | 登录 200/未登录 401；字段与 spec §4 逐项对 | `/api/civil-service/timeline/me` 先例（`exam_timeline.py:80`） |
| 2 | 缺口段数据源正确 | 复用 `settle_checklist`；无目标空态 | `condition_checklist.py:30`（`/my-profile-summary`）|
| 3 | 前端面板挂载 | 考试流程 tab 首屏可见；375px 可读 | `civil-service/page.tsx:274`（timeline tab）、`components/civil-service/exam-timeline.tsx` |
| 4 | 来源角标形态统一 | 域名+可信度+时间；PREDICTED 琥珀"预计" | `exam-timeline.tsx`：STATUS_BADGE `:31`、dateLabel `:41`、调用点 `:227`/`:230`、ShieldCheck 来源块 `:239-244`（**09-15 复测；原写 `:236-244` 已修正**）|
| 5 | 负例 N1-N5 全拒 | 断言打到展示层 | 本文 §3 |
| 6 | **与聊天侧同口径（D6）** | 同一考次同一节点，面板文案/日期/状态 == `timeline_companion` skill 聊天答案 | `skills/timeline_companion.py`；实测并排对账，任一处不一致即口径漂移，判不通过 |
| 7 | 回归与三绿 | pytest 全绿（行数级证据）+ tsc/vitest/build 绿 | 项目惯例 |
| 8 | 增量段（004 后） | 事件接入、SLA 字段对账、watched_sources 非造假 | 004 quickstart §2/§5 |
| 9 | 零推送纪律 | 未新增渠道；Notification 沿用既有（INFO ≤3/天）| constitution 6 |

## §7 冲突面核对（实施时逐条过）

- **09-15 19:2x 复测刷新**（旧快照"exam-timeline.tsx 属 A4 在改"：**已提交历史证伪，但工作区实测又成立**——同一文件以另一形式回到在途）：
  - 已提交历史：`exam-timeline.tsx` 末次**提交** `f82aa44`(001 M4)，A 类已提交批次对它 diff 为空；`civil-service/page.tsx:274` timeline tab 挂载点健在。
  - **工作区**：`frontend/components/civil-service/exam-timeline.tsx` **在途 -9 行**（摘 `n.dark_knowledge` 渲染块，A4 暗知识残留收尾，与已提交 `8f320a5` 同线）。
- **当前在途全量（09-15 19:2x `git status`）**：`AGENTS.md`/`BLOCKED.md`/`PROGRESS.md`/`README.md`/`DOCKER_README.md`/`tasks/plan.md`/`todo.md`/`n8n/SETUP.md`/`docs/competition-2026-ai-talent.md`/`docs/data-leverage-roadmap.md`/`docs/gradpath-future-strategy.md` + `frontend/components/civil-service/exam-timeline.tsx`(-9) / `types/index.ts`(-75) / `kaoyan/compare`(-21) / `search` / `war-room` / `lib/api/grad.ts`(-1)。
- **判定与处置**：① 这不是 005 实施（无人在抢做伴跑面板，全部是同一条 A4 暗知识收尾线）；② **T4 的挂载文件 `exam-timeline.tsx` 在途 → T4 必须等这笔记完**（T1/T2/T3 面不受影响，可先做）；③ 005 目标类型面 `frontend/types/exam-timeline.ts` **未被动**（对方动的是 `types/index.ts`）。
- **新增需盯**：**A9**（"备考工具" tab 语义待拍板：删 or 更名）会改 `civil-service/page.tsx` —— 与本面板**同文件**；若 A9 先落地，实施 T4 前先 `git show <A9 commit> --stat` 看重排后的 tab 结构。
- 规则：**A 类 commit 前不动这些文件**；A 后实施时先 `git show <A类commit> --stat` 看改动面，再动手；`exam-timeline.tsx` 仅顶部挂载（不重构）。
- 若与执行会话同文件撞车：停手 → 报方向席位协调（历史教训：并行同任务撞车时停手转监督位）。