# PROGRESS

## 开工回执（2026-09-05 · 供给增援三件套：记账单行化+扩校+死源注销）
- 目标：①一次爬取恰一行 CrawlerRun（含 started/finished/duration/stored_count/duplicate_count）+ API 兜底路径同修；②official_announce 扩校 ≥6（真实抓取标定+夹具+黄金测试）；③16 个死源 yaml 注销（enabled:false+注释）。
- 顺序：任务0 基线核对 → 任务1 单行化+观测 → 任务3 死源注销（快） → 任务2 扩校标定（网络重） → 全量 pytest → 单 commit（不 push）。
- 最大风险：扩校被高校 WAF/robots 挡（如实记 BLOCKED.md，≥6 校合格线）；PROGRESS.md 为共享文件只追加不覆盖、不纳入本 commit（沿用上会话先例）。
- 纪律：不碰 chsi、≥1.5s/请求、只动 backend/、不 git add -A。

## 状态（供给增援三件套 · 2026-09-05）
- [x] 任务 0 基线：1732 passed 0 failed 0 skipped（任务书预估 ≈1722，实测 +10 为并行会话新增，无失败，无需 BLOCKED）。
- [x] 任务 1 单行化：行以爬虫 store() 创建为准（`BaseCrawler._new_run_record/_finalize_run_record`，started_at=run() 起点、duration ceil≥1s、stored_count/duplicate_count 齐全），run() 结果带 run_id；包装层（crawler_tasks.run_crawler_task / run_scheduled_crawler_task、api/crawlers._run_crawler_background / _run_scheduled_crawler 兜底）经 `_resolve_run_record` 只更新爬虫建的行，未建行（dry_run/建行前失败）才兜底补一行。8 个 research 爬虫（official/rsshub/eol/web_article/bilibili/tieba/rss_news/zhihu）同步改造；grad/ 与 admin/research.py 建行逻辑未动；广播与自动放行保持原样。新测试 tests/test_crawler_run_bookkeeping.py 6 个（单行/二次爬取两行/定时包装单行/失败兜底单行/dry_run 兜底单行/API 兜底单行）。
- [x] 任务 3 死源注销：16 个 yaml（boss/lagou/company_review/interview/salary_data/github_datasets/grad_forum/mentor/scoreline/yanzhao/guokao/shengkao/civil_ratio/civil_salary/pdf_report/stats_importer）enabled:false + 顶部注销注释；example/tieba/zhihu/rsshub/bilibili/position_xlsx 未动。
- [x] 任务 2 扩校：9 校达标收进 DEFAULT_SECTIONS（cms=generic、content_cls 留空自动探测）+ 9 个真实抓取夹具 + tju 详情夹具 + 10 个黄金测试（16 passed）；夹具 sha256 与 docstring 十条全一致（程序化复核）。
- 全量 pytest：见文末「最终验证」。

- 最终验证：commit 8962b2d（不 push）；全量 `cd backend && py -3.13 -m pytest tests/ -q` → **1748 passed, 0 failed, 0 skipped**（基线 1732 + 新增 16，精确吻合）；grep 全测试仅 3 处他文件既有条件 skip（compliance_b5/metrics/web_vitals，实跑均未触发）；PROGRESS.md 与并行会话在途文件（reminder_service.py 等）未纳入本 commit。

## 任务 2 扩校标定证据（2026-09-05 实抓，限速 2s/请求 + robots/SSRF 护栏，脚本 scripts/calibrate_official_announce.py）
- 判定线：列表页 parse_list_generic ≥5 条 + 最新日期 ≤18 个月内（cutoff 2025-03-05）+ 同域；详情 extract_main_text ≥80 字。
- 达标 9 校（≥6 合格线）：

| 校 | list_url | 原始/过滤后条数 | 最新日期 | 详情字数 |
|---|---|---|---|---|
| xjtu | https://gs.xjtu.edu.cn/tzgg/zsgz.htm | 14/14 | 2026-06-26 | 341, 772 |
| whu | https://gs.whu.edu.cn/ | 63/43 | 2026-09-03 | 108, 830 |
| hust | https://gs.hust.edu.cn/ | 34/34 | 2026-09-03 | 2954 |
| sdu | https://yz.sdu.edu.cn/ | 14/14 | 2026-06-29 | 251, 1548 |
| tju | https://gs.tju.edu.cn/ | 13/11 | 2026-09-04 | 1082, 729 |
| xmu | https://gs.xmu.edu.cn/ | 32/31 | 2026-09-04 | 126, 962 |
| cqu | https://yz.cqu.edu.cn/ | 6/6 | 2026-05-29 | 548, 465 |
| scu | https://yz.scu.edu.cn/ | 13/7 | 2026-09-05 | 1918 |
| seu | https://seugs.seu.edu.cn/ | 85/81 | 2026-09-04 | 200 |

- 被挡/不达标（如实记录）：
  - scu 主站 gs.scu.edu.cn：WAF 412 Precondition Failed（全部请求），弃用；经 yz.scu.edu.cn 达标收下。
  - hit（hitgs.hit.edu.cn）：首页可抓但 0 条可解析（JS 渲染列表），无达标栏目。
  - nju（yzb.nju.edu.cn/47831/list.htm）：列表 14 条达标，但详情 extract_main_text 0/2 达标（0 字）。
  - csu（gra.csu.edu.cn）：列表 15 条达标，详情 0/2 达标（0 字）。
  - 域名勘误：武大 yjsy.whu.edu.cn / 山大 yjsy.sdu.edu.cn / 中南 yjsy.csu.edu.cn / 哈工大 yjsy.hit.edu.cn / 天大 yjsy.tju.edu.cn DNS 均不存在；hust yjs.hust.edu.cn robots.txt 禁止（换 gs.hust.edu.cn）；xmu yjsy.xmu.edu.cn robots 禁止（换 gs.xmu.edu.cn）；cqu yjs.cqu.edu.cn robots 禁止（换 yz.cqu.edu.cn）。
- 注：scu/sdu/cqu 的 yz.*.edu.cn 为该校研究生院/研招办运营的校级官方招生网（edu.cn 域，非 chsi）；whu/hust/tju/xmu/scu/sdu/seu 均有 yz 域或 gs 域二选一，取实抓达标者。

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

---

# PROGRESS — 测评结果页三处信任修复（本会话，2026-09-05）

## 开工回执（≤10行）
- 理解的目标：T1 interpret 接用户真实回传分查同分去向（替换写死 None）；T2 信度警告从 result_summary 尾巴上浮为结果区警示卡；T3 paths 非空时结果卡加 /decision-engine 完整报告入口。
- 顺序：T1 → T2 → T3（后端先行，前端两件共用一次 vitest 回归）。
- 最大风险：T2 解析标记串「【作答提示】」是前后端冻结契约，后端改文案即失效（已按书冻结）。
- 任务 0 实测：HEAD=4a208bd ✓、工作区净 ✓、vitest 182 passed ✓、build 绿 ✓（本会话同树实测）、pytest=1723 passed+1 skipped（≠书写的 1687，良性漂移，见 BLOCKED.md，下限上调 1725）。
- PROGRESS.md 为共享文件，本会话只追加本段。

## 进度
- [x] 任务 0：基线核对完成
- [x] 任务 1：同分去向接线（接线+2 pytest+反向验证红→还原绿）
- [x] 任务 2：信度警告可视化（warning-utils 4 例+callout 2 例+page 主结果/历史接线+反向验证红→还原绿）
- [x] 任务 3：决策漏斗闭环（/decision-engine CTA+1 vitest 含空态断言）
- [x] 单 commit + 验收证据（pytest 1725+1skip / vitest 189 / build 绿 / 两 grep 达标）

---

## 状态（抽取升级）
- [x] 任务 0 核对：夹具 sha256 三个一致；trafilatura 2.2.0；hzau_detail 正则346字/trafilatura315字连续含黄金句、结尾2026年6月29日；原型 hzau 7条.htm（含863968无yjsjygk）、uestc 20条。基线偏差（3 failed 属并行会话在途 streak/micro_action 改动）记于 BLOCKED.md 顶部。
- [x] 任务 1：extract_main_text（异常/None/len<80→""）；_fetch_detail HTTP 分支 trafilatura 优先、空则降级原正则；crawl4ai 分支未动；pyproject 加 trafilatura>=2.0。反向验证：恒返 "" → 黄金测试红（assert ... in ''），还原后 6 passed。
- [x] 任务 2：parse_list_generic（bs4+祖先≤4级日期证据+同域去www.+http/https+≥6字+URL去重+日期降序）；_parse_list_entries 加 base_url="" 第三参支持 generic；_fetch_section 传 list_url。反向验证：期望改 99 → 红（assert 20 == 99），还原后绿。
- [x] 全量 pytest：1722 passed 全绿（≥1686；期间并行会话修复其 3 条失败并新增其测试文件，与本任务无关）。夹具 sha256 复核一致；test_official_announce_templates.py diff 为空。
- [x] pre-commit（isort/black/ruff/gitleaks 等）对改动文件全 Passed，无重排需二次 add。
- 备注：PROGRESS.md 为并行会话共用的未跟踪文件，本会话只追加不覆盖、不纳入本 commit（避免代提交他人笔记）；BLOCKED.md 随交付提交。

---

## 状态（增量架构改造：URL去重前移+per-host限速+公告提频+假就业源注销 · 2026-09-05）
- [x] 开工回执：目标=官方公告线改"高频轮询+只抓新 URL"（时差 ~24h→~1h）+修一慢全慢+拔假就业源雷。顺序：任务0基线→4假源注销→2 per-host→1 URL增量→3提频→测试→两遍实证→commit。最大风险：per-host 节流若锁跨 sleep 持有会退化回全局串行（已规避：锁只护字典，sleep 在锁外）。执行 agent 两次被并发上限杀掉，管理者本人直执（有 assess-moat 先例）。
- [x] 任务 0 基线：1798 passed 0 failed 0 skipped（并行会话持续加测试，较 1750 又涨）。
- [x] 任务 4 假就业源注销×5：boss(random.seed(42):198)、lagou(random.seed(42):120)、interview(_COMPANIES:24/116)、review(_COMPANIES:21/91)、salary(_COMPANIES:21/195)——docstring 自证"生成 N 条"零真实抓取；@register_crawler 注释禁用+证据注记，文件保留；salary_expand 无合成实锤未动；ALLOWED_CRAWLER_SOURCES 本就不含五者，compliance 测试不受影响。
- [x] 任务 2 per-host 限速：BaseCrawler 节流改 _last_request_ts_by_host 分桶 + _throttle(host) 方法（锁只护字典读写，绝不跨 sleep 持锁）；同域间隔 ≥rate_limit 不变；official concurrency 默认 1→4（跨域并行、同域串行）。
- [x] 任务 1 URL 增量：fetch() 前经 _load_known_urls()（复用 research_ingestion._load_kaoyan_dedup_baseline，失败返空集退化为全量）加载基线；_fetch_section 抓详情前 normalize_url 命中即跳过并计 known_skipped（stats 透传 run 结果）；store 层 simhash/URL 去重原样兜底。
- [x] 任务 3 提频：DEFAULT_DAILY_SCHEDULES official_announce "0 2 * * *"→"0 * * * *"；seed 迁移逻辑：job 存在且 cron≠默认 → replace_existing 覆盖+日志（取舍：管理员改频属极小概率按"默认即真理"，改频后会被 seed 覆盖回默认）；新增 _job_cron_str 比对。
- [x] 新增 tests/test_crawler_increment_and_throttle.py 9 例（同域间隔/跨域无等待/双域并行吞吐/全已知零详情/半已知只抓未知/基线失败退化空集/默认 cron 锁/seed 替换迁移/假源注销断言）。
- [x] 增量两遍实证（uestc 夹具 20 条）：首遍详情请求 20、known_skipped=0、0.19s → 次遍详情请求 0、known_skipped=20、0.02s。生产规模推算：50 校单轮 ~30min→约几分钟，高频轮询每小时仅 11 个列表请求。
- [x] 全量 pytest：1812 passed 0 failed 0 skipped（基线 1798 + 本活新增 9 + 并行会话在途 5，精确吻合）。部署不进本活。

---

## 状态（Top50 扩标定批跑 · 2026-09-05 晚，管理者直执）
- 标定脚本升级（fa0f8cd 后）：双模板判定（generic/boda 择优出 cms 字段）+ PASS 校直接产出 DEFAULT_SECTIONS 条目 + CANDIDATE_SCHOOLS 增 22 校。冒烟 uestc/fudan 双过。
- 批跑结果：批1 1/7（fudan PASS；tsinghua/sjtu/tongji/buaa NO_LIST=大校 SSO/JS 站，pku/zju ERROR）；批2 5/7（bit/ruc/ecnu/hnu/lzu PASS；bnu/scut=域名猜错 DNS 拒）；批3 4/7（jlu/zzu/nwpu/ccnu PASS；dlut 详情 0/2、njust ERROR、ecust DNS）。**新达标 10 校：fudan bit ruc ecnu hnu lzu jlu zzu nwpu ccnu**（+uestc 冒烟过未存）。
- 下一步：①--save 补夹具（11 key：fudan uestc bit ruc ecnu hnu lzu jlu zzu nwpu ccnu）②DEFAULT_SECTIONS 增 10-11 条（section 条目已在脚本输出）③test_extraction_upgrade.py 参数化黄金测试加新校 ④pytest 全绿→commit→bundle 部署 ⑤失败校如实记 BLOCKED（大校 SSO/JS 类需浏览器渲染立项；bnu=yz.bnu.edu.cn、scut=yz.scut.edu.cn 待重试）。

## 状态（Top50 扩展批完成 · 2026-09-05 晚）
- 3b6c022 上产：DEFAULT_SECTIONS 11→22 校（新增 fudan/uestc/bit/ruc/ecnu/hnu/lzu/jlu/zzu/nwpu/ccnu），数据驱动封印复现测试（20 份 calibration.json 全纳管），1848/0/0。生产 sections=22 实证、冒烟 200。
- 覆盖评分卡：22/50 校、时差 ≤1h、断供发现 ≤90min（data_freshness cron）。
- 待立项：大校 SSO/JS 站（清华/上交/同济/北航/南大/中南/哈工大/大工）需浏览器渲染；bnu=yz.bnu.edu.cn、scut=yz.scut.edu.cn、ecust 域名待修正重试；就业线真供给选型。

## P2 功能合并（执行中 · 2026-09-06 · 生产基线 6b9d070）
- 理解目标：菜单每组只留折叠后主入口，八条旧路由 302，成就墙吸收成长洞察，三绿收尾。
- 顺序：任务0 基线(lint 0 error/vitest 183 绿 skipped=0/build 过，已验) → 任务1 nav+命令盘 → 任务2 redirects → 任务3 合页 → 任务4 三绿 → 部署+暗卷。
- 最大风险：并行会话同仓活跃（工作区 8 条脏项），只动书内白名单文件；/decisions 302 会让个人中心"决策记录"tab 落到决策中心，属书内拍板照走。
- 裁量记录：任务1"决策组只留 decision-center"按书让步顺序与"零数据丢失"意图收窄为只删书内拍板折叠的入口（engine/lab/life-wheel/career/insights）；career-simulator、micro-actions、retrospectives、growth-archive、life-design 无 redirect 拍板，保留在导航防失联。
- P2 结果：任务1-4 全过。nav/命令盘删 8 折叠入口（grep 实证空）；redirects 8 条 302（python 逐条 source_hit=1）；GrowthInsight+NewBadgeToast 并入成就墙（achievements 10.1kB/insights 241B 壳）；vitest 183 绿 skipped=0；lint 0 error；build ✓。待部署。

## 爬虫闸门防守第一批（执行中 · 2026-09-06 · deploy-rebased@6b9d070）
- 理解目标：chsi 红线四处焊死（官方域名表/入库/promote/yanzhao 伪URL）+ Celery 白名单复查 + zhihu/tieba 死源下架 + 15 名退役 + registry==whitelist 机器不变量 + 部署冒烟。
- 顺序：T1 焊红线 > T2 复查 > T3 退役 > T4 提交部署；全量 ≥1853 绿为闸。任务0 实测：1853 passed 0 failed（422s）、registry=25 与书一致。
- 最大风险：冻结文件 test_compliance_b5:121 断言 "mentor 已注册" 与领导拍板"mentor 注销"互斥——最小翻转该行前置断言并记 BLOCKED.md 待领导复核，其余冻结断言一字不动。
- 生产影响预告：入库闸生效后，存量 PENDING 里的 chsi 伪 URL 条目人工放行会失败（设计内行为），复审时按拒绝处理；本批零迁移零数据改动。
- T1 ✅ chsi 四处焊死（官方域名表删除/入库咽喉拒收+计数/promote raise 纵深/yanzhao 伪URL→校主页或 curated://），新增 tests/test_chsi_redline_gate.py 6 条；反向验证：拆入库闸→红→还原→绿；yanzhao grep chsi=0。既有测试改动 3 处（授权后果）：test_research_queue test_official_domain 样例换 edu.cn、test_ingestion fixture 11 处 chsi 样例换清华研招页（fixture 借用非断言）。
- T2 ✅ 两个 Celery task 开头加 is_allowed_crawler 复查，tests/test_celery_whitelist_guard.py 5 条。**过程教训**：首版测试断言串与外层 catch-all 报错串撞词造成「假绿」，反向验证拆守卫时当场暴露（红不出=测试无牙），改精确匹配守卫专属报错串+REGISTRY-REACHED 越界探针后双侧红→绿齐。
- T3 ✅ zhihu/tieba 出白名单+注销+yaml false；15+salary_expand（补账，见 BLOCKED#4）共 16 处 @register 注释带 @RETIRED；新增 test_crawler_registry_invariant.py 3 条（registry==whitelist==10 冻结+退役防复活）；反向验证：注册幽灵爬虫→不变量精确点名 ghost_crawler 红→删→绿。b5 按 BLOCKED#1 改 5 处（前置翻转/403→403∪404×2/dict+键×2）。
- 中途并行会话提交 f063b37（P2 前端），本工作基于其上；commit 一律显式路径，排除他人改动的 docs/承诺台账.md。
