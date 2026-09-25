# Implementation Plan 008：缓存修复 + 死代码清场（T1–T5）

> 方法论：planning-and-task-breakdown（轻量档）。
> **T1（P0）单独 commit 先行**，T3–T5 可合并批次；与 005/006/007 零文件冲突，随时可开。

## 1. Overview

两段：**T1 修一处测试假绿掩盖的生产缺陷**（并顺带把 8 处失效副本收敛成 1 处）；**T3–T5 按审计清单清死代码**。零新功能、零新依赖、零新测试框架。

> **09-15 实施后修正（执行期以本段为准，勿照旧数字动手）**：`git diff --numstat` 实测 **删除 61840 行 / 新增 98 行**，其中 **8158 行是代码**、**53537 行是 archive 里 7 个假数据备份 JSON**（旧稿"−8155 行"只数了 `.py`，引用数≠行数）。**T5 的"−1 依赖"已收回：`pillow` 不许删**——`pyproject.toml:40-52` 注明它是 crawl4ai 依赖链的安全下限（pip-audit 复审钉版），判删标准是"是否仍被上游满足"而非 import 计数。T4 另补一条实施期新发现：`lib/api/skills.ts` 的 `getSkillMap` 死存根（3 行，零调用点且后端 `/api/skills/map` 路由从未存在）随 `types/skills.ts` 一并删除。

## 2. 依赖图

```
T1 失效逻辑收敛 + 端点接入 + 测试穿下游闸（含负例实证）  ← P0，单独 commit
      │
T2 删 event_service.py（仅当 T1 选 A）——可并入 T1 同一提交

T3 删 scripts/archive/          ┐
T4 删前端孤儿模块（含 skills.ts 死存根）├─ 彼此独立，可合并批次
T5 删 cached() 装饰器（pillow 保留）  ┘
```

## 3. Task List

> **09-15 实施状态**：T1–T5 已全部落地于本地工作区（方向席位按用户"开始"直接实施），四绿 + `import app.main` 实证见 `docs/验收清单-2026-09-14.md` §三·九。**未 commit**——commit 与部署归执行会话，故下方 Checkpoint 保持未勾。

- [x] **T1 [P0] 失效逻辑收敛 + 端点接入 + 测试穿下游闸**（M：4-6 文件）
  - Description：
    1. 在 `app/core/cache.py` 加一个方法 `invalidate_user_context(user_id)`（内部即 `delete(f"user_context:{user_id}")`，保留原 try/except 静默语义）。
    2. 按 §2 M1 的 A/B 二选一，让 `api/career_events.py` 三个端点具备失效能力；把 5 个 service 的 `_invalidate_user_context_cache` 与 3 处内联调用全部改为调这一个方法。
    3. 测试改用 `TestClient` 打真实端点并断言缓存被清。
  - Acceptance：
    ① 全仓 `_invalidate_user_context_cache` 定义数 = **1**（或全收敛为 `cache.invalidate_user_context` 调用）；
    ② 端点路径测试绿；
    ③ **负例实证：注释掉端点失效调用 → 测试变红**（附两次运行输出，这是本任务的核心交付）；
    ④ 不改变接口返回体（端点响应结构逐字段未变）。
  - Verify：`cd backend && python -m pytest tests/test_user_cache.py -v` → 负例跑一次 → 恢复；`python -m pytest -q` 全量绿；`python -c "import app.main"`。
  - Files：`app/core/cache.py`、`app/api/career_events.py`、`app/api/assessment.py`、`app/services/{auth,career_plan,decision,skill,retrospective,chat}_service.py`、`tests/test_user_cache.py`。
  - Deps：None。

- [x] **T2 删 `event_service.py`**（S：1 文件；仅 T1 选 A 时执行）
  - Description：T1 让端点自带失效后，`services/event_service.py` 的 CRUD 与端点完全重复且无生产调用者 → 整体删除；`tests/test_user_cache.py` 对它的 3 处 import（:24/:261/:298）随 T1 改到端点路径后一并消失。
  - Acceptance：① `grep -rn "event_service" --include="*.py" backend` 零命中；② `import app.main` 冒烟过；③ 回归绿。
  - Verify：`grep` + `python -c "import app.main"` + `pytest -q`。
  - Files：`app/services/event_service.py`（删）、`tests/test_user_cache.py`。
  - Deps：T1。

- [x] **T3 删归档脚本目录**（S：1 目录）
  - Description：删 `backend/scripts/archive/`（**84 文件 / 59123 行**：76 py 5568 + **7 json 53537** + 1 md 18，0 引用。JSON 系 2026-08-16 假数据清除备份，git 历史即备份，不留）。
  - Acceptance：① spec §2 D1 验证命令输出为空；② `git show --stat` 显示删除规模与 84 文件量级一致；③ 回归绿（该目录无测试依赖）。
  - Verify：`grep -rn "scripts.archive\|scripts/archive" ...` → 空；`pytest -q`。
  - Files：`backend/scripts/archive/`（删）。
  - Deps：None。

- [x] **T4 删前端 9 个孤儿模块 + 1 处死存根**（M：10 文件）
  - Description：按 spec §2 D2 表逐个删（674+467+416+402+214+123+67+50+39 = 2452 行）。
    ⚠️ **09-15 实施修正**：D2 表对 `types/skills.ts` 判错——它并非零引用，`lib/api/skills.ts` 第 2 行有 `import type { SkillMap } from "@/types/skills"`（别名路径 grep 漏判）。处置＝**不恢复 67 行类型，删调零调用点且后端 `/api/skills/map` 路由从未存在的 `getSkillMap` 死存根（3 行）+ 两行 import**（净 1 insert / 5 delete）。
    ⚠️ **闸门电力**：`npx tsc --noEmit 2>&1 | tail` 的退出码是 `tail` 的，会把报错伪装成通过；跑闸用 `node_modules/.bin/tsc --noEmit > /tmp/tsc.out 2>&1; echo exit=$?`（先确认 `cd frontend`）。
  - Acceptance：① 每个模块**逐个**跑导出符号名全仓 grep（排除自身）为空，**别名路径（`@/…`）的引用也算，grep 不算数、以 tsc 为准**；② `node_modules/.bin/tsc --noEmit` **exit 0**；③ `npx vitest run` 绿（实测 156 passed / 17 文件）；④ **删前回报**：若发现 `CommentSection`（社区评论后端仍在）等属"产品还要但 UI 未接"，停下问方向席位，不擅自删。
  - Verify：逐模块 grep + `node_modules/.bin/tsc --noEmit`（取真实退出码）+ `npx vitest run`。
  - Files：9 个前端文件（删）+ `lib/api/skills.ts`（改）。
  - Deps：None。

- [x] **T5 删 `cached()` 装饰器（pillow 保留）**（S：1 文件）
  - Description：删 `app/core/cache.py` 的 `cached()`（37 行 / 0 调用点）。
    ❌ **09-15 收回：`pillow` 不许删。** `backend/pyproject.toml:40-52` 是 2026-09-04 pip-audit 复审的**安全下限钉版**——`aiohttp/pillow/requests/nltk` 系 crawl4ai 依赖链的下界保护，全仓 import 计数为 0 是正常现象。判删标准＝"该钉版是否仍被上游依赖需要"，而非源码有无 import。同类不可按 import 计数判删的还有 `email-validator`（被 pydantic `EmailStr` 运行时加载）。`pyproject.toml` 本次**零改动**（已 `git status --porcelain` 实证）。
  - Acceptance：① `grep -rn "@cached(" backend` 为空（`cached` 作局部变量名的命中不算）；② `import app.main` 仍过、98 路由照常注册；③ 回归绿。
  - Verify：`grep` + `python -c "import app.main"` + `pytest -q`。
  - Files：`app/core/cache.py`。
  - Deps：None（与 T1 同文件 `cache.py`，注意改不同区域，可分开提交）。

### Checkpoint
> ⚠️ **09-19**：工作区有并行会话在途改动（考研工具箱瘦身，`grad_intel*`/`kaoyan`/`commands.ts` 等）——commit 一律显式路径 add，禁 `-u`/`-A`；详见 `docs/验收清单-2026-09-14.md` §三·九 复测警告。

- [ ] T1 单独 commit 落地 + **负例实证输出入证据包**（没有这一步不验收）。→ 负例两次输出**已备好**（注释失效 `3 failed / 10 passed`；恢复 `13 passed`），commit 归执行会话。
- [ ] T3/T4/T5 各自 grep 输出为空 + `git show --stat` 与清单一致（无夹带）。→ grep 已实测为空；`git show --stat` 只能在 commit 后做。
- [x] 四绿：pytest **1896 passed / 1 skipped** / pre-commit `--all-files` **exit 0** / `node_modules/.bin/tsc --noEmit` **exit 0** / vitest **156 passed**。
- [x] `import app.main` 冒烟过（98 路由照常注册）。
- [ ] 部署冒烟绑特有断言（增删职业事件后 `user_context` 缓存确实被清）——待上产后补。

## 4. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 删前端孤儿模块时把"产品还要但未接线"的 UI 删掉（尤其 `CommentSection`） | 中 | T4 验收强制"删前回报"，方向席位确认后放行；不擅自删 |
| 删 `archive/` 卷入他人 staged 删除 | 中 | 用显式路径 `git add backend/scripts/archive/`，commit 前核 `git diff --cached` 清单 |
| T1 的"负例实证"跳过 → 又造一个假绿测试 | 高 | 把负例两次输出列为验收硬门槛；缺则退回 |
| 收敛失效逻辑时改变原静默语义（原实现吞异常） | 中 | 保留 try/except 静默；不做"顺手把异常抛出去"的改进 |
| `cache.py` 被 T1 与 T5 同时改 → 冲突 | 低 | 两任务改不同区域且分开提交 |

## 5. Open Questions（09-15 实施时全部有答案，保留供对账）

- ~~M1 选 A 还是 B~~ → **已选 A**：端点自带失效（`career_events.py` import `invalidate_user_context` 并在 create/update/delete 三处调用），`event_service.py` 随之整体删除。
- ~~`CommentSection.tsx` 是否属"产品仍要、只是 UI 未接"~~ → **已删**（214 行，全仓零引用）。社区评论后端能力仍在，若日后要接 UI，按新需求重做，不从 git 历史复活孤儿组件。
- ~~是否值得为 `user_context` 做全局 SQLAlchemy 监听器式自动失效~~ → 本次不做（spec §5 假设 2 成立），维持显式调用点。
