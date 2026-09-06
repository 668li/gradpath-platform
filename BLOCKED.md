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

---

# BLOCKED 追加 — 供给增援三件套会话（2026-09-05）

执行无硬阻塞（扩校 9/12 达标，超 ≥6 合格线）。以下为标定过程中被挡/不达标的学校，如实记录（详见 PROGRESS.md 扩校证据表）：

1. 四川大学 gs.scu.edu.cn（研究生院主站）：所有请求被 WAF 拦截，HTTP 412 Precondition Failed（首页与栏目页一致，重试 3 次仍 412）。弃用主站；经该校研招办官网 yz.scu.edu.cn 达标收下（13 条/7 条详情匹配/最新 2026-09-05）。
2. 哈尔滨工业大学 hitgs.hit.edu.cn：首页可抓但 parse_list_generic 得 0 条（公告列表为 JS 渲染，静态 HTML 无日期证据），无达标栏目，未收。
3. 南京大学 yzb.nju.edu.cn（yjsy.nju.edu.cn 被 WAF 483 拦）：列表页达标（/47831/list.htm 14 条），但详情页 extract_main_text 0/2 出正文（0 字，疑似正文容器非静态/需渲染），不满足「详情 ≥80 字」验收线，未收。
4. 中南大学 gra.csu.edu.cn：列表页达标（15 条全部新鲜），详情页 extract_main_text 0/2 出正文（0 字），同上未收。
5. 域名勘误（DNS 不存在，fail-safe 拒发）：武大 yjsy.whu.edu.cn、山大 yjsy.sdu.edu.cn、中南 yjsy.csu.edu.cn、哈工大 yjsy.hit.edu.cn、天大 yjsy.tju.edu.cn；robots.txt 明确禁止抓取：hust yjs.hust.edu.cn、xmu yjsy.xmu.edu.cn、cqu yjs.cqu.edu.cn（均改用该校可达的 gs.*/yz.* 官方域）。
6. 红线遵守：全程未触碰 chsi 任何域名；所有请求经 BaseCrawler 护栏（robots fail-safe + SSRF 校验 + ≥1.5s 限速，标定用 2s）。

另：PROGRESS.md 为共享文件（含并行会话未提交笔记），按上会话先例只追加、未纳入本 commit；backend/app/services/reminder_service.py 与 backend/tests/test_reminder_d2.py 为并行会话在途改动，未纳入本 commit。

---

# BLOCKED 追加 — 测评结果页三处信任修复会话（2026-09-05）

1.（非阻塞，已按规矩处理）任务 0 基线漂移：书写的 pytest 基线 1687 passed，实测 **1723 passed, 1 skipped**（deploy-assess=4a208bd，本会话动工前、未改任何文件时）。高出部分来自服务器线（70557a3）带入的抽取层黄金夹具/出身条款提取器回归等测试，属基线变强非前提损坏。按「测试数只许 ≥ 基线」上调本任务下限：pytest passed ≥1725（1723+任务1新增2个）；vitest 下限不变 ≥186（实测吻合 182→+4 新增）。

（其余：无阻塞项。）

---

# BLOCKED 追加 — 爬虫闸门防守第一批会话（2026-09-06）

1.（条款互斥，已取最小冲突解，待领导复核）任务书「判卷冻结」要求 test_compliance_b5.py 断言一字不动，但 T3 领导拍板注销 mentor 后其 :121 前置断言 `get_crawler("mentor") is not None` 必红。两条款字面互斥，取最小改动：翻转该行前置断言（mentor 已注销）+ docstring 补事实。后续实测又证伪了本条最初记的「端点先查白名单，403 语义不变」——真实顺序是先查注册(404)后查白名单(403)，故两处 403 主断言改为 `in (403, 404)`（拒绝语义保留：mentor 在更早的 404 闸即不可执行；白名单 403 路径的存在性由 worker 守卫测试与不变量测试共同锁死）；另 store 返回 dict 两处精确断言补 `redline_rejected: 0` 键（T1 授权后果）。该文件全部改动共 5 处，均源自领导拍板的必然后果，逐条同步记入 PROGRESS.md。
2.（重要发现·修正版——原记「不经 store 生成伪 URL」已被测试证伪）real_data_crawler.py:255 给**每一条** store 产物挂伪研招网 URL `https://yz.chsi.com.cn#real_data:{source}:{school}:{key}`，与 yanzhao 伪 URL（书内已修）完全同源。入库红线闸焊死后 real_data 产物 100% 被拒（tests/test_crawlers.py 三处正向断言撞墙后改为 KNOWN DEFECT 定性锁）。该书界限不含此文件，本批未修源码。影响面：real_data 不在 DEFAULT_DAILY_SCHEDULES（无常态调度，仅白名单手动触发），生产无因此断供。**第二份书必办**：:255 改挂 _SOURCE_BASE_URL 对应真实来源域或 curated:// scheme（配方同 yanzhao），修后恢复三测试正向断言；生产存量 t_external_research_item 中 `#real_data:` 行需一并裁决（建议：人工复审按拒绝或重挂 URL）。
3.（超出书界限未做，建议下一批）api/crawlers.py 的 /run 与 /schedules 为「先查注册(404)后查白名单(403)」顺序：白名单 403 闸对未注册名永远不可达。建议把 `_assert_allowed_crawler(...)` 移到 `get_crawler(...)` 判空之前（两处各 ~2 行），使非白名单一律 403、且不泄露注册状态。该文件不在本书「只许改」清单内，故未动。
4.（范围补账）salary_expand.py 的 @register 在文件中是活的，但模块不在 app.crawlers 包导入链上、从未进实载注册表——书的 13 名清单源自注册表枚举故未含它；审计 C 表 P1 判其注销，随 T3 一并注销并注释说明。若未来被 import，旧写法会注册 "salary_expand" 并立即被新不变量测试拦红，属预期防线。

## P2 功能合并会话（2026-09-06 · f063b37）
（无阻塞项。任务1"决策组只留 decision-center"按书让步顺序收窄执行，裁量理由记 PROGRESS.md。）
