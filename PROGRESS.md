# PROGRESS

## 任务 0 基线（2026-09-04 实测）
- 后端：`cd backend && py -3.13 -m pytest tests/ -q` → 1686 passed（文档 1685，浮动 +1 可接受）
- 前端：`cd frontend && npm test` → 159 passed；`npx tsc --noEmit` → 0 错
- 分支 deploy-rebased；未跟踪文件 backend/tmp_*、backend/tests/fixtures/official_announce/、docs/行为设计执行层加固方案.md 为他人产出，不碰。

## 理解的目标/顺序/最大风险
- 顺序：T1 删假打卡 → T2 真实行为写穿 StreakRecord → T3 允许空串完成 → T4 中断次日提醒 job（默认关）→ T5 前端轮询+续学卡。
- 目标：连击只反映真实行动；中断次日站内收到一条 reminder，dashboard 可续学。
- 最大风险：T2 写穿引入循环导入或破坏既有 streak 测试语义（采用最小调用点注入，不动 streak_service 结构）；T4 scheduler 在测试环境误触发（用幂等注册+开关默认 False 防护）。

## 状态
- [x] 任务 0 基线核对
- [x] 任务 1 P0-1 去掉假打卡（新测试先行红→修复后绿；只删 record_activity 三行，缓存逻辑未动）
- [x] 任务 2 P0-2 真实行为写穿（checkin_action/complete_task 内调 record_activity；反向验证红→还原绿）
- [x] 任务 3 P0-3 允许空串完成任务（schemas 去掉 min_length=1）
- [x] 任务 4 P1 提醒链路（config 默认 False + reminder_service + main.py startup 注册 21:00 cron；筛选单测 9 个全绿 + 反向验证红→绿；测试环境不注册 job）
- [x] 任务 5 P1 前端两件（nav.tsx 60s 轮询；dashboard 续学卡；tsc 0 错、npm test 167 全绿）
- [ ] 提交

## 决策记录
- tests/test_micro_action.py 中旧测试 test_complete_empty_response_rejected（断言空串 422）与任务 3 目标直接冲突，按任务要求改名为 test_complete_empty_response_allowed 并断言 200（测试数不变，行为翻转是任务本身的要求）。
- 写穿实现放在 action_service.checkin_action 的 `_refresh_streak` 调用之后、micro_action_service.complete_task 内；均函数内局部 import streak_service，无循环导入。
- 续学卡渲染内联在 dashboard/page.tsx（白名单不许新建组件文件）；选择逻辑抽成 lib/api/resume.ts 纯函数 findNextPendingTask（白名单内"小 helper"），测试覆盖：helper 5 例 + dashboard 页渲染 3 例。
- reminder_service.send_d2_reminders 调 push_notification（同步过滤 + 异步发送）；job 回调自建 SessionLocal，与 _run_scheduled_crawler 范式一致。
- 注：下方另一份 PROGRESS（官方公告爬虫）来自并行会话，本会话不覆盖其内容。其 BLOCKED 记录的 3 条失败正是本会话任务 1-3 的在途红状态，本会话完成修复后全量 pytest 已恢复全绿（见提交信息）。


---

# PROGRESS — 官方公告爬虫抽取升级（本会话，2026-09-04）

## 理解的目标/顺序/最大风险（≤10行）
- 目标：接新校=加一行 cms:"generic"；正文由 trafilatura 干净完整抽出（HTTP 路径）。
- 顺序：任务0 核对 → 任务1 extract_main_text + _fetch_detail HTTP 分支 → 任务2 parse_list_generic + generic 模板分发 → 全量 pytest → 反向验证 → 单 commit。
- 最大风险：并行会话在途改动污染基线（实测 3 failed 均在其 streak/micro_action 文件，与本任务无关，见 BLOCKED.md）；trafilatura 短页误吞（用 len<80 门槛兜底走原正则）。
- 纪律：只改 official_announce_crawler.py / pyproject deps / 新建 test_extraction_upgrade.py；夹具只读；PROGRESS.md 为共享文件，只追加不覆盖。
