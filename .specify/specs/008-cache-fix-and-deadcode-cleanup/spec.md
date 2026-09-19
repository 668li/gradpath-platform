# Feature Spec 008：缓存失效缺陷修复 + 死代码清场（ponytail 审计落地）

- **Branch**: deploy-rebased｜**Created**: 2026-09-15（方向席位出规格）
- **依据**: 2026-09-15 ponytail 插件全仓过工程化审计（只读实测，可删项逐条验证过引用数）；方法论=ponytail-review（`delete:` / `shrink:` 标签）
- **范围纪律**：
  - **不改任何业务行为**——**唯一例外**是 T1 修的那处缓存失效缺陷，且修的是"本该成立却没成立"的既有意图，不是新增行为。
  - **不新增功能 / 页面 / 端点 / 依赖 / 测试框架**。
  - **只删与被删项相关的引用**；每项删除前**必须复跑本 spec 给出的逐条验证命令，验证不通过即停**，不许"顺手一起删"。
  - 排除清单（§6）里的东西**一律不许删**，那是审计已排除的误报。

## 1. Objective

两件事，优先级不同：

1. **[P0] 修实质缺陷**：`app/api/career_events.py` 的 create/update/delete 三个端点**完全不失效** `user_context:{user_id}` 缓存（该文件连 `cache` 都没 import）；而现有测试 `tests/test_user_cache.py` 把断言打在了 `app/services/event_service.py` 上——**那个 service 生产一条调用链都不到**。结果：**测试绿、线上增删职业事件后用户上下文最长脏 300 秒**。这是"负例测试未穿下游闸"在本项目的**第三次**复发（见 `verify-gate-at-fact-moment-principle`）。
2. **清死代码**：git 实测 **删除 61840 行 / 新增 98 行**——其中 **8158 行是代码**（archive 76 py=5568、前端 9 孤儿=2452、`cached()`=37、`event_service.py`=98、`getSkillMap` 死桩=5，另收敛净删 125），**53537 行是 archive 里 7 个假数据备份 JSON**（`synthetic_purge_2026-08-16/`，另 1 md=18 行）。**依赖一项无可删项**（见 D4 的收回）。

**成功判据（可测）**：① 存在一个**在"端点不做失效"时会变红**的测试（本案验收核心，见 §2 M1）；② 删除项逐条通过验证命令，且 `pytest` / `tsc --noEmit` / `vitest` / `ruff` 全绿；③ `user_context` 失效逻辑从 **8 个失效点收敛为 1 处定义**（两处"超集"保留为委托调用）。

## 2. 执行契约

### M1 [P0] 缓存失效收敛到活路径

**根因**：同一件事（事件 CRUD 后失效用户上下文）有两份实现，测试验证的是生产不走的那份。

| 实现 | 位置 | 是否生产链路 |
|---|---|---|
| 端点自带 CRUD、**无失效** | `api/career_events.py:111/139/164` | ✅ 生产走这条 |
| service 版 CRUD + 有失效 | `services/event_service.py:25/90/98` | ❌ 只被 `tests/test_user_cache.py:24,261,298` 调用 |

**修法（二选一，执行期定并写进提交说明，不许两个都留）**：

- **A（推荐，改动最小）**：`api/career_events.py` 三个端点调用失效函数；`services/event_service.py` **整体删除**（其 CRUD 与端点重复）。
- **B**：`api/career_events.py` 端点改走 `event_service`（端点退化为薄转发），保留唯一实现。

**判据**：最终 `user_context` 失效逻辑**只有 1 处定义，且在生产的调用链上**。

**顺带收敛（`shrink:`）**：同一逻辑现有 **8 个失效点**（5 处函数定义 + 3 处内联），统一为 `app/core/cache.py` 上的一个函数 `invalidate_user_context(user_id)`：

- 5 份 `_invalidate_user_context_cache` 定义：`services/event_service.py:12`、`career_plan_service.py:19`、`decision_service.py:15`、`skill_service.py:11`、`retrospective_service.py:13`
- 3 处内联 `cache.delete(f"user_context:{...}")`：`api/assessment.py:192`、`services/auth_service.py:25`、`services/chat_service.py:523`

**⚠️ 收敛时的回归陷阱（两处是"超集"，不许当成副本直接替换）**：`skill_service.py:11` 还额外失效 `skill_tree:{uid}` / `skill_stats:{uid}` 两个技能域独有键；`auth_service.py:25` 还额外失效 `user:{uid}`。这两处必须改成**委托**共享函数后再补删自己的键，否则删完就漏失效。真正逐字相同的只有 4 处定义 + 2 处内联。

**测试必须穿下游闸（本 spec 的核心要求）**：

- 测试用 `TestClient` 打**真实的** `POST/PUT/DELETE /career-events/*` 端点，断言调用后 `cache.get(f"user_context:{uid}") is None`。
- **负例要求（"测试有牙"的唯一证明）**：执行期**实际**把端点的失效调用注释掉跑一次，该测试**必须变红**，并在证据包里记录这次验证。不做这一步 = 本任务未完成。
- 现有 `tests/test_user_cache.py` 里依赖 `event_service` 的三个用例随之改到端点路径（或随 `event_service` 删除一并处理）。

### M2 死代码清场（逐条已实测零引用）

| # | 删什么 | 行数 | 锚点 | 验证命令（删前必跑，非空即停） |
|---|---|---|---|---|
| D1 | 归档脚本目录 | 84 文件 / 1.62 MB / **59123 行**（76 py=5568 + **7 json=53537** + 1 md=18） | `backend/scripts/archive/` | `grep -rn "scripts.archive\|scripts/archive" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.toml" backend .github \| grep -v __pycache__` |
| D2 | 9 个前端孤儿模块 | 2452 | `frontend/components/preview/eligibility-checker.tsx`(674)、`grad/SelfPositioning.tsx`(467)、`recommend/RecommendPanel.tsx`(416)、`grad/SchoolIntel.tsx`(402)、`community/CommentSection.tsx`(214)、`kaoyan/quality-feedback.tsx`(123)、`types/skills.ts`(67)、`stores/gwy-compare.ts`(50)、`lib/gwy-score-lines.ts`(39) | 每个模块的**导出符号名**全仓 grep（排除自身文件）；返回非空即停。**⚠️ 09-15 实施时实测：本条对 `types/skills.ts` 判错**——它有 1 个真实引用（`lib/api/skills.ts` 的 `SkillMap`）。该文件已连带删除其死桩（见下），非"零引用" |
| D2b | （D2 的连带后果）`skillsApi.getSkillMap()` 死桩 | 3 | `frontend/lib/api/skills.ts` 原 :2 `import type { SkillMap }` + :28-30 方法 | 后端 `app/api/skills.py` 路由实测**只有** `""`/`/stats`/`/batch`/`/{skill_id}`，**无 `/map`**（与 09-14 记忆"能力地图端点从未存在·实测 422"一致）；全仓 `getSkillMap` 零调用者。删桩 = 少删 67 行类型文件的复活代价，且消掉一个必然 404 的入口。`buildQuery` 在该文件仅这一处使用，一并从 import 摘除 |
| D3 | `cached()` 装饰器 | 37 | `backend/app/core/cache.py:188-224` | `grep -rn "@cached(" --include="*.py" backend`（注意：`cached` 作**局部变量名**的命中不算，如 `grad_intel.py:178`） |
| D4 | ~~`pillow` 依赖~~ **已收回，不许删** | — | `backend/pyproject.toml:47` | 见 §6 末行：这是 2026-09-04 pip-audit 复审钉下的 **crawl4ai 传递依赖安全下限**，不是"未使用依赖"。审计原判据（"无 `from PIL` 引用"）对此类钉版失效 |
| D5 | `event_service.py`（随 M1-A 删除时执行；若 M1 选 B 则本项作废） | 98 | `backend/app/services/event_service.py` | 删前先确认 M1 已让端点具备失效能力 |

## 3. 验收（并入 `docs/验收清单-2026-09-14.md` §三·九）

1. **P0 缺陷**（本 spec 最重要的一条）：
   - ① 端点路径的失效测试绿；
   - ② **负例实证**：注释掉端点失效调用 → 该测试变红（附前后两次运行输出）；
   - ③ 全仓 `invalidate_user_context|_invalidate_user_context_cache|user_context:` 的失效定义**收敛为 1 处**。
2. **删除项**：D1–D5 每项的验证命令输出为空（附输出）；`git show --stat` 核对删除规模与 D 清单一致（不许夹带清单外删除）。
3. **回归**：`pytest` 全量绿（行数级证据）+ `pre-commit run --all-files` 干净 + `cd frontend && npx tsc --noEmit` 干净 + `npx vitest run` 绿。
4. **导入冒烟**：`python -c "import app.main"` 通过（防删出 import 断裂——本项目 A4 轮踩过）。
5. **部署冒烟**：HTTPS 站点登录态下增删一条职业事件，绑**本次特有断言**（操作后 `user_context` 缓存被清 / 下一次 AI 对话上下文含该事件），不是"页面能打开"。

**证据包**：按 `docs/验收清单-2026-09-14.md` §一 五件套交付，缺任一件不进入验收。

## 4. 依赖与实施窗口

- **无前置依赖**；与 005/006/007 零文件冲突（本 spec 只碰 `api/career_events.py`、`core/cache.py`、几个 service、`scripts/archive/`、9 个前端孤儿文件）。
- **实施窗口**：随时可开，**不占公告季关键路径**（004 探针期可并行，无共享文件）。
- **顺序**：T1（P0）先行并单独 commit（便于回滚与验收），T2–T5 可合并批次。

## 5. 假设（错了现在纠正）

1. `user_context:{uid}` 那 300 秒的脏读对产品可感知——按 M1-A 修，不引入主动失效以外的机制。
2. 不做全局 SQLAlchemy 事件监听器自动失效（更"根治"但影响面大、绕开既有显式失效风格）——本次只统一到活路径。若后续再出现同类漏失效，再议监听器。
3. `backend/scripts/archive/` 是显式归档目录（含 README），删除后靠 git 历史找回，不需要迁到别处。
4. 前端 9 个模块删后**不重建**；若其中某个功能其实还有用户要（尤其 `CommentSection`——社区评论后端仍在），那是**产品决策**，不在本 spec，删前由执行会话回报确认。

## 6. 禁止删除清单（审计已排除的误报，动它们是错）

| 对象 | 为什么看着像死代码 | 真相 |
|---|---|---|
| `app/api/*`（94 个模块） | 任何地方都没有 `import` | `api/__init__.py:auto_discover_routers()` **目录扫描注册**，是活的 |
| `app/core/cache.py::SimpleCache` | 只在一处出现 | 是 `RedisCache` 的**降级兜底**（`cache.py:81`），Redis 挂时靠它 |
| `crawlers/url_safety.py` 的第二份 robots 缓存 | 与 `base_crawler.py:61` 重复 | 注释明写是给**测试 monkeypatch 留的接缝**（`url_safety.py:120-125`），刻意拆的 |
| `app/skills/_skill_template.py` | 无引用 | **文档化模板**（`docs/skill-registration-checklist.md` 指它） |
| `crawlers/run.py`、`app/seed/*` | 无 import | **入口脚本**，按 `python -m` 跑 |
| Next.js `app/**/page.tsx` 等 | 无 import | **路由约定**加载 |
| `pyproject.toml` 的 `pillow`/`aiohttp`/`requests`/`nltk`/`soupsieve`/`starlette`/`cryptography`/`setuptools` | 源码里 `from X import` 命中为 0 或极少 | **安全下限钉版**（`pyproject.toml:40-52` 注释逐条写明）：强制 crawl4ai / beautifulsoup4 / python-jose 等**传递依赖**到已修复版本。"无人 import"正是它们存在的意义——**这类行的删除判据是"下限是否仍被上游满足"，不是"是否被 import"** |
| `email-validator` | 全仓零 import | `pydantic` 的 `EmailStr` 运行时按字符串加载该包，删了 **启动即报** |
| `email-validator` 依赖 | 源码里 0 次 `email_validator` | pydantic `EmailStr`（`schemas/auth.py` 3 处）**运行期必需**，删了注册就崩 |
| `psycopg2-binary` / `python-multipart` / `python-json-logger` / `soupsieve` / `setuptools` / `scikit-learn` / `aiohttp` / `pyyaml` | 包名在源码里搜不到 | 包名≠模块名（`yaml`/`sklearn`/`psycopg2`/`multipart`…），均**有真实引用** |