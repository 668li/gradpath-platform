# BLOCKED（待裁决清单）

## 基线偏差：全量 pytest 非全绿（3 failed），全部来自并行会话在途改动，与本任务无关
- 任务书称开工基线 `py -3.13 -m pytest -q` = 1686 passed 全绿。实测（2026-09-04，本会话动工前、未改任何文件时）：
  `3 failed, 1687 passed, 25 warnings in 396.62s`
- 失败用例：
  - tests/test_micro_action.py::TestCompleteTask::test_complete_empty_response_rejected
  - tests/test_p0_streak_fixes.py::test_action_checkin_writes_streak_record
  - tests/test_p0_streak_fixes.py::test_micro_action_complete_writes_streak_record
- 归因：工作区存在并行会话未提交改动（git status: M backend/app/schemas/micro_action.py、M backend/app/services/dashboard_service.py、?? backend/tests/test_p0_streak_fixes.py），其 PROGRESS.md 显示 P0 任务 1-3 未勾选，属其在途半成品。失败全部集中在 streak/micro_action 域，与本任务允许的 3 个文件零交集。
- 处置：不碰、不回滚他人文件（死规矩）。本任务「全量 pytest 全绿」判定标准相应记为：除上述 3 条并行会话失败外无其他失败，且 passed ≥1686。若管理者要求严格全绿，需先处置并行会话在途改动。

## 顺手活禁令确认（未做，按任务书要求列明）
- base_crawler requests→httpx：未做。
- 安装 curl_cffi：未做。
- 动 dedup.py / research_ingestion.py：未做。
- DEFAULT_SECTIONS 加新校（含电子科大）：未做。
- 解析 PDF 附件：未做。

## 其他
- 无（除上述基线偏差外，无待裁决项；未新增 trafilatura 以外依赖）。

---

# BLOCKED 追加 — P0 三修+P1 提醒链路会话（2026-09-04）

执行期间无阻塞。以下为按「界限」主动搁置、未动手的顺手活，留待裁决：

1. push_notification（app/api/notifications.py:282）无 link 参数，通知不能携带跳转地址。若希望 reminder 通知点击直达 /micro-actions，需要给 push_notification/Notification 加 link 字段（涉及 models + API，超出白名单，未做）。前端续学卡用固定跳转 /micro-actions 代替。
2. streak_service.record_activity 与 checkin 功能重叠（checkin 内部即调 record_activity），可合并精简；本次只加写穿调用点，未重构（界限点名不许顺手重构）。
3. 上文「基线偏差」记录的 3 条失败，实为本会话任务 1-3 的在途红状态（先写测试后修复的 TDD 流程），本会话已修复：test_complete_empty_response_rejected 改名为 test_complete_empty_response_allowed（任务 3 翻转该行为），两条写穿测试已绿。非数据或环境问题。
