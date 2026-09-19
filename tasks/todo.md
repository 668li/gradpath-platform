# Todo: 产品瘦身后的伴随层收敛（2026-09-13）

## A 类：机械执行（等你一句"开工"）

- [x] A1 [P0] 删两个假数据 skill（registry.py:59 社区内容生成器 / :155 种子数据生成器 + 实现链 + registry==whitelist 测试）— ✅ commit `9ca120f`
  - Acceptance: 生产 /skills 不可见；grep 无残留；回归绿
- [x] A2 删上岸报告+导师评价+上岸墙（community Tab 收敛 feed；outcome-report 页面群+API+model 下线；mentors API+页面下线；先查 share 引用；生产先备份；向量层对账）— ✅ commit `80da68d`（后端）+`7816ebc`（前端）；mentors 表 drop 挂台账
  - Acceptance: 三处入口全消失；生产 grep 无路由残留；回传 E2E 不受影响
- [x] A3 删 AI 生成计划（study-plans/ai-generate 整页+入口+api/ai_study_plan.py）— ✅ commit `82535db`
  - Acceptance: 入口消失；手工建计划不受影响
- [~] A4 考研暗知识全删（knowledge 页+dark_knowledge_push API+civil tab+kaoyan 入口；删除清单先列后删）— **在途：删除已 staged 未提交；引用残留 5 处已清零、双 import 冒烟过（09-14 深夜方向席位实证）；待 commit+回归+证据包**
  - Acceptance: 知识入口全消失；白名单同步；回归绿
- [ ] A5 首页三线覆盖（app/page.tsx 考公-only 文案 → 考研/考公/就业/在校）
- [ ] A6 决策中心点击无效果：诊断→修→带特有断言冒烟
- [ ] A7a 能力地图加载失败：生产 API 实测→诊断→修→冒烟
- [ ] A7 移动端命令面板可达 + 面板条目/真实路由 100% 对账
- [ ] A8 /admin 三层验证（nav 门控✓已有 / 路由守卫 / API 403），缺则补
- [ ] A9 备考工具 tab：随 B 类拍板（删 or 更名保留）

## B 类：拍板点（我已给答案，等你同意/修改/否决）

- [ ] B1 ✅09-14改写：行动层=pull式缺口漏斗面板（节点×缺口×情报增量，打开可见）；推送钩子取消；90天冲刺/学习计划折叠进时间线；09-18 续做率按面板口径重读
- [ ] B2 ✅09-14强化：吸引=敢说真话/可信/懂你（全pull交付）；"准时"卖点随提醒击毙一并取消
- [ ] B3 ✅09-14击毙提醒版：日历降级为缺口面板数据基建（规则预填PREDICTED+官方硬更新）；台账公开墙=二期可选
- [ ] B4 路径模拟器收敛为三线各一条主路径，数据只用已有真实表+诚实空态
- [ ] B5 AI 对话 skill 收敛 10→4（流程伴随官/公告解读/人生设计/通用咨询-明示走搜索）
- [ ] B6 专业前景做结论层（6档出身个性化+条件账本联动），不做聚合搜索入口
- [ ] B7 人生设计蓝图行动→条件账本/时间线；测评溶解进对话+ask-matt 4修清账
- [x] B8 ✅09-14 集成规格已出：用户提供 `$ai-project-fupan` skill（复盘三角×双我思维×原则库，虚舟《复盘》）→ **006 spec `.specify/specs/006-fupan-method/`**（记录→反思→提炼三步产品化；原则入 user_memory `principle` 类型经 build_context_prompt 注入对话；三闸：材料不足不硬编/空话不入库/未确认不落库）

## C 类：待你输入

- [ ] C1 复盘 skill 文件
- [ ] C2 暗知识之后"什么信息值得"你自己重新想（B3 可先承接）
- [x] C3 Trae/GitHub 灵感调研已交付：docs/灵感聚合调研-删完靠什么吸引-2026-09-13.md（吸引点 Top5，B1/B3 证据齐可先拍）

## D 类：008 缓存修复 + 死代码清场（09-15 ponytail 审计落地，**可即时开工，零文件冲突**）

> 规格：`.specify/specs/008-cache-fix-and-deadcode-cleanup/`（spec + plan）；验收：`docs/验收清单-2026-09-14.md` §三·九。

- [x] D1 [P0] **修缓存失效缺陷**：`api/career_events.py` 三端点无 `user_context` 失效，而测试断言打在**生产零调用**的 `services/event_service.py` 上 → 测试绿、线上脏 300s。修法 **已选 A**（端点 import `invalidate_user_context`，create/update/delete 三处调用）+ 8 处副本收敛为 1 处（`skill_service`/`auth_service` 两处**超集**改委托，勿当副本删）+ **测试改打真实端点**。**负例硬门槛已实证**：注释失效 → `3 failed / 10 passed`，恢复 → `13 passed`
- [x] D2 删 `services/event_service.py`（98 行，与端点 CRUD 重复）
- [x] D3 删 `backend/scripts/archive/`（84 文件 / **59123 行**：76 py 5568 + **7 json 53537 假数据备份** + 1 md 18 / 0 引用）
- [x] D4 删前端 9 个孤儿模块（2452 行）；`CommentSection`（214）经查全仓零引用、社区评论后端仍在但 UI 属可重做，**已删**；⚠️ 实施期 tsc 驳回一处误判：`types/skills.ts` 实有别名 import（`@/types/skills`），连带删 `lib/api/skills.ts` 的 `getSkillMap` 死存根（零调用点 + 后端 `/api/skills/map` 路由从未存在，见 D5b）
- [x] D5 删 `core/cache.py::cached()` 装饰器（37 行 / 0 调用点）；~~+ `pillow` 依赖~~ **已收回：pillow 是 crawl4ai 依赖链的安全下限钉版（`pyproject.toml:40-52`），不许删；判删标准是"是否仍被上游满足"，不是 import 计数**
- [x] D5b（实施期新增）删 `lib/api/skills.ts` 的 `getSkillMap` 死存根 + 2 行 import（净 1 insert / 5 delete）

**禁区**：spec §6 排除清单里的对象（`app/api/*` 自动注册模块、`SimpleCache`、robots 测试接缝、`_skill_template`、入口脚本、`page.tsx`、**`email-validator`**、**`pyproject.toml` 安全下限钉版族 aiohttp/pillow/requests/nltk/soupsieve/setuptools**）**一律不许删**。
**规模**（09-15 git 实测）：**−61840 行 / +98 行**，其中代码 8158 行、archive 内假数据备份 JSON 53537 行；**依赖一项无可删项**。改动 94 删 + 11 改，D1 单独 commit 先行，D3–D5 可合并批次。
**状态**：本地全部落地、四绿实证，**未 commit**（commit + 部署归执行会话）。⚠️ **09-19 复测警告**：并行会话的考研工具箱瘦身正在同一工作区在途（删除 94→107、numstat −67822/+135，含 `grad_intel*`/`kaoyan`/`onboarding`/`commands.ts` 等在途改动与未跟踪 `_tmp_batch2_surgery.py`）——**D 类 commit 必须按上方 Files 清单逐路径显式 `git add`，禁 `git add -u`/`-A`，commit 前逐项核 `git diff --cached`；当前树 numstat ≠ 008 规模**。详见 `docs/验收清单-2026-09-14.md` §三·九 复测警告。

## 执行顺序

A1 → A2/A3/A4 → A5/A8 → A6/A7a → A7；B 类按拍板结果排队；D 类（008）可随时插入（零冲突）；每步部署后 git show --stat 验内容。
