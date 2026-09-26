# Spec: 011 信任对齐第一批（承诺-兑现对齐：考公退役收尾 + 诚实报错 + SEO 真域名）

- **Normative version:** `011-trust-alignment-batch1 v1 (2026-09-26)`（本文件为不可变身份；变更走后继规格+逐 ID delta）
- **Predecessor:** none（本规格是 2026-09-26 已拍板"考公线退役"（commit 4b77ebe）与"bilibili 删线"的**执行收尾**，不是新方向；证据基线=docs/信任缺口调研-2026-09-26.md）
- **External decision ledger:** `docs/承诺台账.md`（生命周期状态记录于此；本规格一经批准不再编辑）
- **Decision owner:** 用户（唯一拍板人）；执行会话持实现权；调控席（本会话）持验收权
- **冻结窗注记：** 用户于冻结窗内（2026-09-26）直接以 /spec-it 指令授权本规格，属明示豁免；本批性质为已拍板工作的漏刀收尾，非新立项。

## Problem

生产实测证明：站点对陌生人的信任崩塌来自"承诺与兑现的差值"——首页/引擎/决策中心多处仍在**承诺已不存在的能力**（三路口径、考公岗位分析、缓存钉死的退役页壳、占位域名元数据、误导性报错）。本批把这些"说了没做"的点全部对齐到"做得到的说法"。服务于目标：推广就绪（陌生人凭链接走完核心闭环不遇到假承诺）。

## Requirements

每条为可观察行为；ID 稳定永不回收。验收形式按"最便宜的诚实形式"选择；标注"Planned gate"的门由执行会话在实现时落进项目真实测试体系。

| ID | Must do | Acceptance form | Artifact today, or gate + owner |
| --- | --- | --- | --- |
| R-01 | `POST /api/path-decision/analyze` 的 `recommendation` 在任何输入组合下（个人条件包全填/部分填/全空、含/不含 estimated_score）不含"考公""行测""申论""岗位分析""可报边界""三条路"字样；填了条件时仍输出个人条件行（两路口径，考研估分语义保留） | executable gate | Planned gate：扩展 `backend/tests/test_path_decision_engine.py`（文件现存）断言关键词集合为空——owner 执行会话；另加一条生产 curl 抽测（部署冒烟） |
| R-02 | 引擎全链用户可见文案为两路口径：`frontend/app/(app)/decision-engine/page.tsx`（h1/副标题/空态）、`engine-form.tsx`（表单标题/hint/条件包文案）、`backend/app/api/path_decision.py`（docstring 与 router tag）不含"三条路/考公/岗位表/行测/申论"；空态不承诺已删除的数据面（"岗位表"） | source-fact contract | Planned gate：`grep -rn "三条路\|考公\|岗位表\|行测\|申论" <上列路径>` 输出为空（排除 \_\_tests\_\_）——owner 执行会话；伴随 tsc 全绿 |
| R-03 | 决策报告"行动时间线"（`decision-report.tsx` `buildTimeline`）不输出任何国考/省考/考公应届节点；保留考研/就业节点；"毕业"条目不引用考公窗口；保留"具体以官方公告为准"口径 | executable gate | Planned gate：vitest 对 buildTimeline 输出断言关键词为空——owner 执行会话 |
| R-04 | 决策回传与示例模板不再引导考公：`outcome-form.tsx` 去向选项、`decisions/page.tsx` 示例模板画廊、`reciprocity-block.tsx`/`share-report-actions.tsx` 分享文案中，考公分支对用户不可见（历史数据兼容口径见 Edge-2/3） | executable gate | Planned gate：vitest 渲染断言（选项/模板/分享文案不含"考公"）——owner 执行会话 |
| R-05 | 测评解读卡（`interpret-card.tsx`）在任何数据态下不出现"考公进体制"标签与考公岗位分析内容；其数据源（major_prospect 聚合的 civil_service 字段）是否随之后台下线由设计定，前端可观察要求不变 | source-fact contract + executable gate | Planned gate：grep interpret-card 路径零"考公"命中 + vitest 渲染断言——owner 执行会话；实现前先实测后端字段现状（Open-Q2） |
| R-06 | 情报页（`intel/page.tsx`）及全站导航不存在指向 `/civil-service` 的入口 | source-fact contract | Planned gate：grep `"/civil-service"` 于 frontend/app+components（排除考试时间线 API 调用与测试）为空——owner 执行会话 |
| R-07 | 登录态访问 `/civil-service`、`/career-simulator`、`/civil-service/positions`、`/civil-service/province-positions`：不得返回含退役前内容的 200 页壳（现网实测 x-nextjs-cache HIT, s-maxage=31536000 吐旧壳）；实际行为必须是 307→/dashboard 或 200 的明确退役说明页；**重新部署后复测不得复活** | executable gate（生产冒烟） | Planned gate：部署后登录态 curl 脚本断言（配方=tests/e2e/prod-acceptance.spec.ts 既有登录态注入）——owner 执行会话；实现机制（force-dynamic/revalidate/部署清缓存）由设计定，规格只锁可观察输出 |
| R-08 | 生产环境 `robots.txt` 的 Sitemap 行、`sitemap.xml` 全部 `<loc>`、首页 `og:url` 均为 `https://quxianglab.cn`，任何环境输出不得为 `gradpath.example.com`（现根因=robots.ts/sitemap.ts/layout.tsx:30 的 `NEXT_PUBLIC_SITE_URL` fallback） | executable gate（生产冒烟） | Planned gate：部署后 `curl https://quxianglab.cn/robots.txt` `/sitemap.xml` + 首页 HTML 断言——owner 执行会话；env 注入 vs 改 fallback 由设计定 |
| R-09 | 决策实验室"保存并 AI 分析"：AI 生成失败时用户看到的文案如实区分（"已保存，AI 分析生成失败"类），且 `decision_analyses` 记录已落库可回看；仅当保存本身失败才提示保存失败（现 catch-all 把两者混为"保存失败，请重试"，`decision-lab/page.tsx:171-202`） | executable gate | Planned gate：vitest 组件测试 mock 两种失败态断言 toast 文案与落库行为——owner 执行会话 |
| R-10 | LLM 上游返回 4xx/5xx 时：后端日志包含上游响应体（error code，如 `Arrearage`）而非只有状态码（现 `ai_service.py:128` raise_for_status 吞 body）；用户侧错误信息与日志可区分"账户/配置问题"与"服务暂不可用" | executable gate | Planned gate：pytest mock httpx 400+响应体，断言日志记录含响应体关键字——owner 执行会话 |
| R-11 | 兼容护栏：本批改动后全量测试基线不回退（pytest 全绿、tsc exit 0、vitest 全绿、E2E 孤儿零新增）；a11y 违规数不高于现基线；清理文案时不得删除仍被引用的共享符号（`PATH_LABELS`/`LEVEL_DESC` 等先抽测引用再动） | executable gate | 现有真实门：pytest/vitest/tsc/pre-commit 命令即跑——owner 执行会话 |

## Carried guardrails and obligations

| Obligation | Applies because | Requirement it binds |
| --- | --- | --- |
| Trust/data：真实数据零造假、不承诺未上线能力（page.tsx:12 自述纪律） | 本批存在的理由就是承诺兑现差值 | R-01/R-02/R-03/R-08/R-09 |
| Compatibility：`path_comparisons` 历史记录含考公路 metrics 与 position_analysis 字段，历史回看不得 500 | 引擎两路化已落库历史数据仍带旧结构 | R-01/R-04/R-11 |
| Operational/recovery：单文件 bind-mount/缓存复活前科，部署后必须复测而非只看构建成功 | T3 实测缓存钉死 + 9/25 镜像旧内容四联征 | R-07/R-08 |
| Accessibility：E2E a11y 违规现基线不恶化 | 面经库 211 违规存量在案 | R-11 |

## Edge cases and scenarios

- **Edge-1**：个人条件包全填 + estimated_score 填 → `_personal_condition_line` 删除后 recommendation 的个人条件行改为两路口径输出（考研估分仍参与冲稳保派生），不是简单消失。
- **Edge-2**：历史回传数据 `outcome.selected_path="civil_service"` 在结果页/历史列表的展示——兼容显示为中性"已退役去向"或原样文本，由设计定；不得因 PATH_META 删键而渲染报错。
- **Edge-3**：`destination_type` 枚举含 civil_service 属 DB/Schema 层——本批只动用户可见面（UI 选项隐藏），枚举本身不动（见 Open-Q1）。
- **Edge-4**：`position-analysis-card.tsx` 被 `decision-report.tsx` 与 `assessment/interpret-card.tsx` 双引用——删除组件会破测评模块 import（tsc 抓）；清理顺序必须先处理 R-05 再评估组件去留，TS 孤儿判据只认 tsc。
- **Edge-5**：`NEXT_PUBLIC_SITE_URL` 修复若走"改 fallback"路径，不得影响本地 dev 已注入 env 的行为；若走"构建注入"路径，docker build-arg 变更会使对应层缓存失效（部署耗时预算内可接受）。
- **Edge-6**：R-07 的缓存修复在**下次重部署**时必须仍然成立（ISR 缓存复活前科），验收门含重部署后二次复测。

## Assumptions and dependencies

| ID | Taken as true | Evidence / state | Validation action | Owner | Fresh until | If it fails |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 下一批部署会重建 frontend 镜像（R-07/R-08 的修复需新构建才生效） | gradpath-deploy 管道实证：update_from_bundle.sh 无条件重建 backend/frontend | 执行会话部署时核对镜像 build 时间戳 | 执行会话 | 10/2 | 若走快路径则 R-07/R-08 无法生效——必须走重路径 |
| A2 | og/sitemap 假域名根因=生产构建缺 `NEXT_PUBLIC_SITE_URL`（fallback 生效） | robots.ts/sitemap.ts/layout.tsx 源码 fallback + 生产实测输出 example.com | 部署构建环境 `printenv NEXT_PUBLIC_SITE_URL` | 执行会话 | 实现时 | 根因若另有其他（如 CDN 层），R-08 验收门仍以生产实测输出为准 |
| A3 | 冻结窗执行已获用户明示豁免 | 用户 2026-09-26 直接下达 /spec-it 指令 | — | 用户 | 10/2 | 无 |
| A4 | `backend/tests/test_path_decision_engine.py` 现存且可扩展 | 2026-09-26 本会话刚改过（3→2 metrics 断言） | 实现时打开文件确认 | 执行会话 | 10/2 | 换等价测试文件承载 R-01 门 |
| A5 | interpret-card 的考公数据源现状未知（major_prospect 后端可能仍输出 civil_service 字段） | 双代理未覆盖该字段后端输出 | R-05 动刀前先 curl 实测 /api/major-prospects 输出 | 执行会话 | R-05 实现前 | 后端仍输出→后端字段同批下线或前端过滤（设计定） |

## Open questions and risks

- **Open-Q1**：`destination_type`/`PATH_LABELS` 层面的 civil_service 枚举是"UI 隐藏保留"还是"全链删除+迁移历史数据"——涉及生产数据迁移，超出本批（执行件）权限，留给 P 层拍板；本批按"UI 隐藏保留"实现。
- **Open-Q2**：interpret-card 考公内容的后端数据源现状（A5）——R-05 动刀前必须实测，避免删错供给给其他模块的字段。
- **Risk-1**：本批触碰 `path_decision_engine.py` 的 recommendation 拼装——该函数 9/25 曾因删共享符号翻车（`_BG_DISCRIMINATION_LABEL` NameError）；实现时只动文案拼装行，不做"顺手重构"。
- **Risk-2**：R-02 的 grep 闸可能误伤测试夹具中合法引用考公的负例测试——闸的排除规则（`__tests__`/`.test.`）在实现时校准。
- **Risk-3**：首页 H1"准时推你一把"（P5）**不在本批**——若用户随后拍板改口号，走 P5 单独件，避免本批范围膨胀。

## Out of scope this round

- P1（AI key 充值/BYOK）、P2（106 条 bilibili 帖清理）、P3（ext_research 3553 行甄别）、P4（考研时间线事件线/首页宣传位下线）、P5（首页 H1 口号改写）、P6（分数线数据底座重建专项）——全部见 docs/信任缺口调研-2026-09-26.md §四，各自待拍板后另立规格或任务书。
- 决策中心空账本冷启动（归 010 主线）。
- 浏览器像素级全站走查（marathon Phase A 范围）。
