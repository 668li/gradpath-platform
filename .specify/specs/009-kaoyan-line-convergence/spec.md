# Feature Spec 009：考研线收敛——假链拆除收尾 + 信息差候车室归口

- **Branch**: deploy-rebased｜**Created**: 2026-09-19（规格席位；用户 grilling 拍板 Q1-Q8 全按推荐）
- **依据**: 考研工具箱生产实测（scoreline/暗知识/调剂=0 行、intel 仅 15 带源、news 2803 唯一活资产、self_positionings=4 次使用）+ `delivery/GradPath计划书-信息差伴随层-2026-09-12.md` 红线 5 + `docs/综合调研v2-第一性原理与对抗审查-2026-09-14.md`（差异化=跨线×缺口×信任锚×敢说真话）+ 聚合站实测地图 09-06/09-19 两轮
- **拍板记录（2026-09-19）**：①死链全删；②/kaoyan 留子站瘦身归口；③15 intel+150 研招节目留"信任锚橱窗"；④集成=外链目录+收录管道两模式、搬运入库禁、**站点清单=用户点名制（零预填）**；⑤导师评价类默认零收录（实测全灭站，点名制覆盖）；⑥A9 备考工具 tab 更名"外部工具"保留；⑧单独立 009；**⑨（追加）kaoyan_news 存量 2803 条不保留**——资讯供给改为自建爬取管道集中爬取，爬取目标用户未想清楚、明确挂账（本 spec 只做清空+管道休眠，不定义新管道）

## 0. 现状对账（2026-09-19 工作区实测，动手前必须复测）

**共享工作区已有一批未 commit 的在飞删除**（执行会话进行中，009 不得重复、不得抢提交）：

- 前端 `kaoyan/{compare,predict,strategy,schools}/` 已删；`lib/api` 中 schoolCompareApi/schoolAnalystApi/admissionApi 已清；`kaoyan/page.tsx` 已改双 tab（资讯/社区），假数字 206/588 已删
- 后端 `school_compare.py`/`school_analyst.py`/`admission_predict.py` 已删；`grad_intel.py`+`grad_intel_service.py` 定位链 -653 行
- 同批含 008 ponytail 在飞件（cache.py/event_service.py/archive），**归属各自独立 commit**，009 不混入

**009 只定义下述增量**。开工前置：在飞批已 commit 并收敛生产、`git show --stat` 对账毕、pytest/tsc/vitest 全绿。

## 1. Objective

把考研线从"半死工具堆"收敛为**信息差候车室**：零造假残留、零维护包袱、2027-08 窗口重开时可从资讯/日历供给无爬取重建。四件增量：

1. **残余对账收尾**：SelfPositioning 模型与表的 drop 迁移（生产 4 行无保留价值，备份照惯例留容器 /tmp）；kaoyan_news 存量按拍板⑨清空（移动目标、以清空时刻实数为准：备份→停喂入→清行→复查无回流→管道代码休眠保留，作为未来自建管道的地基）
2. **主页归口**：考试流程时间线 + 社区 + 外链目录 + 橱窗入口；资讯中心 tab 在新供给建立前隐藏（空壳不上线）
3. **信任锚橱窗**：15 条院校情报 + 150 条研招节目带源展示，未命中明说 + 外链研招网
4. **外链目录两线复用**：目录数据形态两线共用（考研主页区块 + 考公"外部工具"tab）；资讯供给重建（爬什么）=用户挂账，想清楚后另案立项

**成功判据（可测）**：①全仓 grep 零死路由、零硬编码院校概率数字；②橱窗只展示带源数据、未命中必外链；③目录零预填、每站必带性质标注；④1896 基线测试全绿不回退；⑤kaoyan_news 存量清零且备份可恢复、ingestion 管道代码在库休眠。

## 2. 执行契约

### T1 残余对账收尾（依赖在飞批 commit 后）

- `models/grad_intel.py` 的 `SelfPositioning`（self_positionings 表）：补 **drop 迁移**（与挂账的暗知识四表 drop 迁移同一批或紧随，用户已批 drop 方向）；删 `grad_intel_service.py` 残留 SelfPositioning 引用（09-19 实测 line 200/215 尚存）；schemas 对账清零
- `kaoyan_news` 存量处置：**先停喂入再清**（09-19 席位复测：管道仍在进数——approved 2816 行、7 天 +27、最新 09-18 入库；spec 撰写时的 2803 是快照，**一律以清空时刻实数为准，禁止锚死数字**）：停定时拉取/ingestion 调度（具体开关以代码实测为准）→ **全量备份双份（容器 /tmp + 宿主机 ~/）并核行数=清空前行数** → 事务清空 → 复查无回流；**ingestion/审核队列/RSSHub 路由代码全部保留休眠**（停调度不停代码），即未来"自建爬取管道"的现成地基
- 全仓对账 grep（零命中为准）：`kaoyan/compare|kaoyan/predict|kaoyan/strategy|kaoyan/schools|school-compare|school-analyst|api/admission|positioning`（考研语义）；对外文案 grep：`206|588`（考研语境）
- 测试对账：删除面的测试已随在飞批清除，补一条负例——`GET /api/grad-intel/positioning/latest` 等旧端点 404

### T2 主页三件套归口

- `kaoyan/page.tsx`：标题改"考研信息站"（或候车室口径，文案执行时定，禁"一站式工具"旧话术）；tabs = 考试流程时间线（复用 001 已上产 tab 路由，执行时核实现路径）/ 社区交流；**资讯中心 tab 隐藏**——存量清空后空壳不上线，新供给落地时随未来另案恢复（/kaoyan/news 页面保留、空列表诚实态）
- 欢迎卡改外链目录区块（T4 数据）+ 橱窗入口（T3）；不新增后端端点

### T3 信任锚橱窗（Q3）

- 最小只读页 `/kaoyan/vault`：数据源=现存 grad-intel 只读 API（intel 列表 + yanzhao 列表，路由名执行时核对）；每条带**简章/官网源角标**（点击可溯）
- 未命中诚实纪律：搜索无结果 → 明示"我们没有该校的有源数据" + 研招网官方查询外链（仅 `<a>` 外链，yz.chsi.com.cn 不可自动请求）
- 硬红线：任何 LLM 补洞、任何无源展示、任何"概率/分数线"类自造数字 = 判不通过；scoreline/adjustment 表 0 行不展示空区块

### T4 外链目录（Q4 修订版 + Q6/A9）

- 共享数据形态 `ToolLink { name, url, category: official|commercial|ugc|archive, note }`，前端静态常量承载（零后端零迁移）
- **清单初始为空——用户点名制**：用户点名 → 执行会话实测（可达性/RSS 可行性/robots/性质）→ 回报 → 用户确认 → 入目录。09-19 侦察档案（chinakaoyan/yanxian/考研帮/kaoyan365/eol 五站可达）仅备查，**不构成添加依据**
- 考研落点：主页目录区块（T2）；考公落点：`civil-service/page.tsx` tab label "备考工具"→"外部工具"（line 25），内容只留真实可达工具，同形态渲染
- 每站必带性质标注 + 一句话定位；ugc/archive 类必须附风险注记

### T5 资讯供给重建（挂账——拍板⑨，目标未定不施工）

- 用户拍板：存量资讯不保留，未来**自建爬取管道集中爬取**；爬取目标（爬什么）用户未想清楚，**本 spec 不定义、不预研、不施工**
- 本 spec 对资讯面只做两件事：存量清空 + 管道休眠保留（T1）；主页资讯入口隐藏（T2）
- 展望期纪律（未来立项时原样带入）：站点/源收录=用户点名制；搬运入库禁；红线域判定用完整域名匹配；RSSHub 路由验证在服务器环境做（本机海外端点被网络层重置，不可作为验证依据）

## 3. 验收

1. **本地**：/kaoyan 主页（时间线/社区 + 目录区块 + 橱窗入口）可达、资讯 tab 不渲染；375px 可读；civil-service"外部工具"tab 正常
2. **负例**：①旧路由/旧端点全 404；②橱窗搜索乱造校名 → 显示"无有源数据"文案 + 外链，**不出现**任何编造条目；③目录为空时显示引导文案（"待站长点名收录"类）而非假列表；④gh 全仓 grep 死引用零命中
3. **数据面**：drop 迁移后生产 self_positionings 表不存在（备份先行）；kaoyan_news 行数=0 且 24h 后复查仍 0（清空时刻实数双份备份先行、备份行数与清空前行数可对账、可恢复）；grad_school_intel=15 / grad_yanzhao_programs=150 两数不回退（09-19 生产基线实测吻合）；ingestion 管道代码在库（休眠非删除，调度停）
4. **测试**：pytest 基线全绿、tsc exit 0、vitest 全绿；负例测试入库
5. **部署冒烟**：gp-preflight 四闸 → bundle → converge → `git show --stat` 验内容 → HTTPS 登录态实测（特有断言：/kaoyan/vault 200 且首条带源角标；/kaoyan/compare 404）

## 4. 依赖与实施窗口

- **前置**：在飞批（考研删除+008）commit 并收敛生产后开工；与 005/007 增量零文件冲突（009 只动 kaoyan 页面族 + civil-service 一行 label + 新增 vault/目录常量）
- 顺序：T1 → T2/T3/T4 可并行 → T5 为规则落地（随首个点名站实测走一遍即算验收）

## 5. 非目标与挂账

- **资讯供给重建（拍板⑨）**：爬取目标（爬什么）用户未定，明确挂账；想清楚后另案立项（009 增量或 010），届时点名制/搬运禁/红线域规则原样带入；休眠的 ingestion 管道是现成地基
- **Q7 其余方面**：用户声明"集成只是一方面"，其余方面未分享——分享后可作 009 增量或 010 另案
- `/kaoyan/study-plans`（用户自建计划 CRUD）与 `/kaoyan/community`（80 帖）**本 spec 不动**；泛自律折叠按 B1 判据另案
- dark_knowledge 四表 drop 与 war-room 残留：既有挂账，随 B2 全 pull 重设计合并，不入 009
- 就业线维持红线 5，本 spec 零触及
- 先验修正入档：gk100 "403 防盗链"已不复现（09-19 复测明细页完整返回）；职友集维持排除
