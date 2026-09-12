# Feature Spec 002：爬虫地基（六块收敛 + 死重根除）

- **Branch**: deploy-rebased（生产权威链由 gp-converge 收敛，不建 speckit 特性分支）
- **Created**: 2026-09-12 ｜ **定位**: Phase 2 官方源捕获的地基——先打管子，再放水
- **依据**: 《数据地基蓝图-可持续低维护-2026-09-06》（方法层，六块+死因五条+验收四判据）、《数据地基-三线施工图》、《数据管道实测报告》、《聚合站实测地图》、当日全库侦察（topology.sh + crawlers 目录 12 万行对账）
- **宪法**: .specify/memory/constitution.md 8 条全适用（零造假/定位红线/合规爬取/时间诚实/工程纪律/部署纪律）

## 1. Overview

把现有爬虫代码收敛到《数据地基蓝图》的六块机制上（**收敛，不是重写**），并根除不适格的死代码/假管道残余。目标是：目标站改版只在合并前爆炸（fixture 疫苗）、死线必被知（心跳+隔离）、假数据构造上无法入库（三态证据）、加一条新线是一个机械动作（声明式契约）——为 Phase 2「官方源公告捕获」提供可直接放水的地基。

## 2. 现状对账（2026-09-12 实测侦察，全部有文件佐证）

| 块 | 现状 | 判决 |
|---|---|---|
| ① 统一请求层 | `_request` 只是 BaseCrawler 方法（requests 实现）；**16 个文件裸用 httpx 绕过护栏**，含白名单活跃源 real_data_crawler.py:16 | 半成品，必修 |
| ② parser 纯函数+fixture | research 线达标（official_announce 有 46 个录制样本 fixture）；grad 线（yanzhao 9,296 行）parse 为类方法+内联常量 | 半成品，本期补疫苗不改 yanzhao 结构 |
| ③ 声明式注册表 | 双轨：compliance.py 白名单恰 10 源（不变量测试锁死）+ 19 个 config yaml + real_data/sources.yaml 三套语义 | 双轨合一 |
| ④ 状态表/游标 | **空白**（全库无 cursor/etag/断点；唯一增量机制是 official_announce 的内存 URL 基线） | 必建 |
| ⑤ 入库咽喉+三态 | PENDING 闸+chsi 红线拒收已硬（有测试）；**fetched/curated/ugc 三态不存在**，t_external_research_item 无证据列 | 必建 |
| ⑥ 台账+心跳+隔离 | t_crawler_runs 台账+data_freshness 表在；**10 源仅 eol_kaoyan 回写心跳；无自动隔离** | 必补 |

**死重**：app/crawlers 共 177 文件/约 12 万行，活跃不足 5k 行。已实锤的字面量假爬虫（scoreline_real 命名造假实锤）、real_data/ 下 ~90 个一次性脚本（含 `import random` 造假生成器 salary_expand 978 行）、嵌套重复目录 real_data/real_data/、8 个 RETIRED 大文件（dark_knowledge_crawler 单文件 29,630 行）仍占位。

## 3. User Stories

- **US1（加线的人）**：以后加一条新爬虫线 = 放一个 yaml + 一个纯函数 parser + 两个录制样本，跑一遍测试即完成接入；不需要读懂任何已有爬虫的代码。
- **US2（维护者）**：某站改版时，CI 在合并前红掉指向具体 fixture；某线死了/被反爬拦截时，新鲜度看板变红并自动隔离该线，其余线无感，库里不会被灌垃圾。
- **US3（数据消费者/用户）**：从系统里看到的每条外部数据，要么带真实抓取证据（HTTP 状态+时刻+内容哈希），要么显式标注 curated/ugc；「无证据的 fetched」在构造上写不进库。
- **US4（审计者）**：打开仓库，爬虫目录里只有白名单 10 源+地基机制+其测试；历史假管道/一次性脚本/已退役大文件物理消失（git 历史可考古，工作区不可复活）。

## 4. 红线固化（违者数据视为假数据，宪法级）

- **R1 零造假**：本工程不产生任何一条生产数据；「虚构源」演练只存在于测试进程，不进白名单、不进库、不进调度。
- **R2 研招网/学信网(chsi 系)不碰**：现有 `_REDLINE_HOSTS` 拒收闸保留并有测试；新传输层继承同闸。
- **R3 职位表内容不解析不入库**：职位 xlsx 归档管道按宪法**不删不跑**；gwy API 处置属独立挂账不在本期。
- **R4 白名单冻结**：ALLOWED_CRAWLERS 恰 10 名不变；扩白名单必须显式 diff+评审（registry==whitelist 不变量测试保留）。
- **R5 全域禁 reset --hard/force**；提交只按显式路径 add（共享工作区，他人未提交条目不卷入）。
- **R6 宁缺毋假**：修不好的线就隔离，绝不用低质量解析或合成数据凑数。

## 5. Functional Requirements

| # | 要求 | 优先级 |
|---|---|---|
| FR1 | **①统一传输层**：app 级统一请求函数（httpx 骨干）：per-host 限速（静态页 ≥0.5s、文件下载 ≥2s）、robots 检查、SSRF 校验（复用 url_safety）、错误分类（4xx 不重试、429 停 20s、5xx 指数退避）、每次请求返回抓取证据（状态码+时刻+内容 sha256）。BaseCrawler._request 委托它，签名兼容；白名单 10 源**零裸外发请求**（守卫测试锁定） | P0 |
| FR2 | **③声明式线契约**：`sources/*.yaml` 一线一文件（name/entry/schedule/budget/sla_hours/window/crawler/target），加载器校验「yaml 名 ∈ 白名单」硬闸；调度默认任务从 yaml 生成（现 DEFAULT_DAILY_SCHEDULES 5 条 cron 值不变）；不变量测试：10 白名单源人人有 yaml、yaml 名越界即红 | P0 |
| FR3 | **④状态表**：新增 `t_crawler_source_state`（source 主键、cursor JSONB、etag/last_modified、last_ok_at、consecutive_fails、isolated、isolated_reason）；运行前读游标、成功后写回；official_announce 的库内 URL 基线迁入 cursor | P0 |
| FR4 | **⑤三态证据**：t_external_research_item 增 `data_origin`（fetched/curated/ugc/legacy；新写入禁 legacy，存量回填 legacy）+ `fetch_evidence` JSONB；入库咽喉强制：data_origin=fetched 必带完整证据（http_status/fetched_at/sha256），缺一拒收该条（不入库、记账可见）；负例测试 | P0 |
| FR5 | **⑥心跳全覆盖+自动隔离**：所有爬虫运行记账钩子统一回写 data_freshness（10 源全覆盖，eol 手写段改走统一钩子）；parse 失败率>30%（≥10 条样本）或连续失败 ≥2 个运行 → 置 isolated 并由调度器跳过，隔离态在新鲜度看板可见；解除隔离是显式人工动作 | P0 |
| FR6 | **②疫苗扩展**：eol_kaoyan 解析抽为模块级纯函数+录制样本 fixture（≥2 页）；「虚构源契约演练」测试：测试内一条 demo 线三文件（yaml+parser+2 样本+断言）走通加载→解析→（测试内）入库校验全链 | P0 |
| FR7 | **死重根除**：删除清单见 plan（scoreline/admission_ratio 字面量假爬虫、real_data/ 全目录+嵌套 dup、career/ 5 爬虫、8 个 RETIRED 大文件、zhihu/tieba/v2ex 等）；每删必 grep 引用→同步 __init__/测试→全量 collect 绿。registry 不变量测试的退役名单保留（防复活语义不变） | P0 |
| FR8 | **四条验收判据测试化**（见 §7），全部进 CI 可跑 | P0 |

## 6. 范围排除（不做清单）

- **不新增任何真实供给线**（eol_fsx/省考扩省/年报管道等属 Phase 2，等拍板后按本期契约机械加线）。
- **不动 yanzhao 预置数据本身**（curated:// 诚实标注已在；grad_catalog 真线替换属 P1 后续拍板）。
- **不动 gwy API/职位三表处置**（独立挂账：数据删除属生产数据手术，需用户单独拍板）。
- **不动 dark_knowledge push 读路径**（37 行存量来源列挂账中）。
- **不动审核队列/晋升链语义**（PENDING 闸已硬，只加三态不改造）。
- 不引任何框架（scrapy/redis/celery-beat 等），APScheduler+httpx 够用十年。

## 7. Acceptance（蓝图四判据，全部测试化）

1. **加线是机械动作**：虚构源演练测试走通「yaml+parser+2 录制样本→加载校验→解析→证据校验」全链；操作步骤文档化后，加一条真实静态线 ≤30 分钟。
2. **改版在合并前爆炸**：故意改坏一个录制样本的关键结构 → 对应 fixture 测试红（演示方式：测试内置一个「坏样本」负例，断言解析器对结构漂移报错/零产出）。
3. **死而被知**：模拟某线 last_ok_at 老化超过 2 个 SLA 周期 → 新鲜度状态翻转为 stale；隔离态由调度器真实跳过（测试覆盖）。
4. **无证据必拒**：喂缺证据的 fetched 条目 → 拒收且不入库（负例测试）；喂 legacy → 拒收。
5. 工程面：pytest 全量绿（先修复本地 trafilatura 缺失导致的 20 个收集错误）；pre-commit --all-files 过；gp-preflight 四闸过；bundle 部署上产 + HTTPS 冒烟；registry==whitelist==10 不变量在产仍真。

## 8. Notes / Assumptions

- A1：删除是收敛的一部分：白名单/registry 语义不变，删的是「无注册的死文件」，不改变任何在产行为；每删一组跑一次 collect 防断链。
- A2：迁移需在 SQLite(dev)/Postgres(prod) 双跑；JSONB 列沿用 external_meta 先例；迁移前实测 prod alembic current（现 f1a3b5c7d9e2）。
- A3：httpx 已在依赖中；requests 仍留在 BaseCrawler 兼容面，但骨干换 httpx 是 BLOCKED.md 挂账的销账。
- A4：三态的 curated/ugc 本期只做「记录与放行」，不做策展工作流 UI（那是回传器/运营的事）。
- A5：本 spec 只管地基；「往地基里放什么水」（哪些新线、什么节奏）由 Phase 2 官方源计划单独拍板。
