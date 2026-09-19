# Feature Spec 006：复盘方法论产品化（B8 · ai-project-fupan 集成）

- **Branch**: deploy-rebased（生产权威链由 gp-converge 收敛，不建 speckit 特性分支）
- **Created**: 2026-09-14（规格席位）｜ **来源**: 用户提供 `$ai-project-fupan` skill（《复盘》虚舟 · 复盘三角）× GradPath 复盘页现有链路
- **依据**: `.specify/memory/constitution.md`（零造假/时间诚实/身份覆盖）；`tasks/plan.md` B8；`docs/下一阶段计划-2026-09-14.md`
- **方法论**: spec-driven-development（本文件=Phase 1）+ planning-and-task-breakdown（plan.md）

## 1. Overview

**产品定义**：把 ai-project-fupan 的三步闭环（**记录→反思→提炼**）从"CLI skill 提示词"产品化为 GradPath 复盘页的原生流程：

1. **记录（过电影）**——用**站内真实留痕**回放过程，不凭印象：时间线节点回传（done/uncertain/skipped）、行动钩子完成、条件账本缺口变化、职业事件（STAR）。零造假：没有留痕的时段如实说"无记录"，不编内容。
2. **反思（双我思维）**——AI 先复述用户原判，再切换"高要求评审者"资格连问（需求是否具体可验收/验收标准是否先于执行/是否反复卡同一环节/是否漏了边界约束），最后返回"最尖锐的一条反驳"。
3. **提炼（原则库）**——产出**一条**行动指南（用户的语境、≤30 字、具体可执行），入库到用户长期记忆（新增 `principle` 类型），**自动复用于 AI 对话**（现有 `user_context_service` 注入链）。

**用户价值**：复盘从"生成一段总结"升级为"产出一条下一次用得上的原则"，且原则在后续对话里被 AI 记住——与护城河（记忆感 003）同源。

**为什么落在现有复盘页**：不新建页面（沿用 B4 收敛原则）；复用 `retro_ai_service`（LLM 调用）、`RetroAIPanel`（面板形态）、`user_memory_service`（归档与注入）。

## 2. User Stories

- **US1（材料回放）**：用户选时段 → 面板"记录"段自动列出该时段站内留痕（节点回传/行动/缺口/事件），每条带日期与来源；无留痕时显示"该时段站内记录较少"并给补记录入口，不编造。
- **US2（双我反思）**：点"反思推演"→ LLM 输出结构化四段：①我的原判 ②评审者逐条挑战（反方清单四问）③我的回应 ④**最尖锐的一条反驳**（必给）。
- **US3（原则提炼）**：点"提炼原则"→ LLM 产出 1–2 条候选原则（格式：原则/触发场景/下回动作/来源/日期）；用户**必须确认后**才落库（防赶复盘、防自动反应归因）。
- **US4（空话防堵）**：若原则是空话（如"要细心"），后端校验/LLM 二次追问，逼到"具体到能执行"（含动作动词或校验项）才允许入库；用户可手动改写。
- **US5（原则库+复用）**：复盘页展示我的原则库（列表+删除）；原则随 `user_context_service` 注入 AI 对话（下次聊天时 AI 已记得"你上次复盘定的原则"）。
- **US6（诚实与局限）**：材料不足 → 标注"低置信度初步判断"并建议先补记录（对应 skill 的 STOP 闸）；结构性约束（缺数据/平台限制）如实标注为局限，不强行开药方。

## 3. 功能需求

| # | 要求 | 优先级 |
|---|---|---|
| FR1 | **记录段聚合**：`GET /api/retrospectives/replay`（登录，时段参数）——聚合该时段：时间线节点回传、行动钩子、条件账本变化、职业事件；每条 `{date, type, text, source}`；零 LLM | P0 |
| FR2 | **反思段 LLM**：`POST /api/retrospectives/review-draft`（登录+限流复用 RETROSPECTIVE_AI_DRAFT）——双我思维 prompt，返回四段结构化 JSON（my_view / reviewer_challenges[] / my_response / sharpest_challenge）；材料不足时 `low_confidence=true` | P0 |
| FR3 | **原则提炼 LLM**：`POST /api/retrospectives/principle-draft`——输入=反思结论（+可选用户补写），输出 1–2 条候选原则（格式见 US3），含空话检测（后端规则：无动作动词/长度过短/纯形容词 → 标记 `needs_refine=true`） | P0 |
| FR4 | **原则库落库**：`UserMemoryFact` 扩展——`MemoryFactType` 新增 `principle`；存储=fact_key=`principle_{n}` 或语义 key，fact_value=原则正文；触发场景/下回动作/来源/日期放 `fact_value` 的结构化尾部（或复用现有字段，执行期定）；**用户确认后**才 `POST /api/user-memory` 入库 | P0 |
| FR5 | **原则库展示**：复盘页新块——按 `fact_type=principle` 拉取（复用 `GET /api/user-memory` 过滤）、展示/删除/反馈（复用既有端点）；空态=引导做第一次复盘 | P0 |
| FR6 | **对话复用**：确认 `user_context_service._serialize_memory_fact`/`build_context_prompt` 把 principle 注入对话 prompt（现有链，无需新代码则仅测试断言） | P1 |
| FR7 | **防御闸**：① 材料不足不硬编（low_confidence + 引导补记录）；② 空话不入库（needs_refine）；③ 落库前用户确认（前端强约束，后端可加 `confirmed=true` 字段）；④ 每时段原则条数上限（如 ≤3）防刷 | P0 |

**不做**：不替代既有 STAR 草稿（保留）；不做团队/组织级复盘（skill 明确判停）；不做自动归档（skill 要求用户确认）；不新增页面；不做情绪处理专项（skill 边界：情绪走 emotion-flag-retro，产品内不建）。

## 4. 数据契约（草稿，执行期以代码为准）

```jsonc
// GET /api/retrospectives/replay?period_start=..&period_end=..
{
  "period": {"start": "2026-08-01", "end": "2026-09-14"},
  "items": [
    {"date": "2026-09-01", "type": "timeline_feedback", "text": "广东报名节点：已完成", "source": "exam_timeline"},
    {"date": "2026-09-05", "type": "action_hook", "text": "...", "source": "action_hook"},
    {"date": "2026-09-10", "type": "condition_gap", "text": "成绩单未上传", "source": "condition_checklist"},
    {"date": "2026-09-12", "type": "career_event", "text": "...", "source": "career_event"}
  ],
  "material_status": "ok"          // ok | thin（薄 → 前端提示低置信度）
}

// POST /api/retrospectives/review-draft
{ "period_start": "..", "period_end": "..", "my_view": "可选：用户先写的原判" }
// →
{ "my_view": "...", "reviewer_challenges": ["...", "..."], "my_response": "...",
  "sharpest_challenge": "...", "low_confidence": false }

// POST /api/retrospectives/principle-draft
{ "review": { ...反思返回... }, "note": "可选：用户补写" }
// →
{ "principles": [ {"text": "<=30字", "trigger": "何时用", "next_action": "下回动作(含prompt片段/校验项)",
                   "needs_refine": false} ] }
```

**原则入库存法（待执行期定细节）**：`UserMemoryFact(fact_type=principle, fact_key="principle_<date>_<n>", fact_value="<原则正文>｜触发：…｜下回：…｜来源：<复盘 id>｜<日期>", source="user_provided", confidence=90)`；不复用 `behavior`（语义不同，防污染既有检索）。

## 5. 验收（详见 quickstart.md）

1. 本地：时段→replay 聚合正确（各源条数与 DB 对账）→review 四段结构→principle-draft 候选→确认入库→原则库可见。
2. 负例：无留痕时段 low_confidence=true 且不编内容；空话原则 needs_refine=true 被拦；未确认不入库；每时段超 3 条被拦。
3. 注入断言：principle 出现在 `build_context_prompt` 输出（穿到 prompt 文本层断言，防假绿）。
4. 部署冒烟：HTTPS 登录态全链一次（含原则库可见/删除）+ 特有断言。

## 6. 依赖与前置

- **A 类批次 commit 后实施**（retrospectives 页/pages 不在 A 在途冲突面内，但共享工作区纪律照常）。
- 既有链路复用：`retro_ai_service.py`（LLM 调用范式）、`user_memory_service.py`（归档/注入）、`retro-ai-panel.tsx`（面板范式）。
- 迁移纪律：`MemoryFactType` 加枚举值需 Alembic 迁移（PG enum）；迁移前实测生产 `alembic current` 作 down_revision、单头自检（constitution 7）。

## 7. 假设（错了现在纠正）

1. "弄到这里面"=集成进 GradPath 产品（复盘页），不是改 CLI skill 本体；skill 本体作为方法论来源留档。
2. 原则库落点=用户长期记忆（`UserMemoryFact`），因其已有注入链（`user_context_service`→chat）与 CRUD API；不新建表。
3. 入口=复盘页扩展（现有 `RetroAIPanel` 加两段）+"原则库"块；不新建页、不进主导航。
4. 每时段原则 ≤3 条；空话检测用规则（动作动词/长度/形容词黑名单）+ LLM 追问双保险。
5. 既有 STAR 草稿（`ai-draft`）与规则版 draft 全部保留，本 spec 只增不改。
6. 复盘页在 A 类瘦身中未被删（已核实：A2 删除的是上岸报告/导师评价，复盘页保留；决策页"回传跳转换复盘链"改动只涉及跳转）。