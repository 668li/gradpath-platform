# Implementation Plan 006：复盘方法论产品化（B8 · ai-project-fupan 集成）

> 方法论：planning-and-task-breakdown——垂直切片、依赖图、每任务显式验收+验证、检查点。
> 实施窗口：**A 类批次 commit 之后**；共享工作区纪律照常（开工前 `tools/topology.sh` 对账）。

## 1. Overview

在既有复盘页内落地"记录→反思→提炼"三步闭环：新增 replay 聚合端点（真实留痕）+ 双我反思 LLM 端点 + 原则提炼端点 + 原则库（用户记忆 `principle` 类型）+ 前端面板扩展。全部复用既有链路（retro_ai_service / user_memory_service / RetroAIPanel）。

## 2. Architecture Decisions

- **D1 增量不改旧**：既有 `ai-draft`（STAR 草稿）/`draft`（规则版）/`weekly-draft` 全部保留；本 spec 只加新端点与面板新块。
- **D2 记录段零 LLM**：`replay` 纯 DB 聚合（时间线回传/行动钩子/条件缺口/职业事件四源），先实证再反思（skill 的第一性：没有记录就没有发生）。
- **D3 LLM 输出结构化四段**：反思走 `retro_ai_service` 同款 JSON 容错解析范式（`_parse_llm_json`/`_coerce_draft` 模式）；prompt 内置"反方清单四问"（skill §E3）。
- **D4 原则库=用户记忆**：`MemoryFactType` 加 `principle`；存储规范见 spec §4；**不复用 `behavior`**（防污染既有检索）。**落库前用户确认**（前端强制；后端加 `confirmed` 语义）。
- **D5 双保险防空话**：规则检测（动作动词/长度/纯形容词黑名单）标记 `needs_refine` + LLM prompt 内要求"具体到能执行"；前端对 needs_refine 强制改写后再提交。
- **D6 复用注入链**：`user_context_service._serialize_memory_fact` 已序列化全部 active facts（含新类型）→ `build_context_prompt` → chat；FR6 仅需**断言测试**（穿到 prompt 文本），无新代码则不加代码。

## 3. Dependency Graph

```
[既有] career_events / timeline feedback / action_hook / condition_checklist ──→ T1 replay 端点
                                                                                    │
                                                                              T2 反思端点（双我）
                                                                                    │
                                                                              T3 原则提炼端点（含空话规则）
                                                                                    │
[既有] user_memory_service/API ──→ T4 principle 类型+迁移 ─→ T5 前端三段扩展+原则库块
                                                                                    │
                                                                              T6 注入断言+全链演练
```

实施顺序：T1→T2→T3→T4→（检查点）→T5→T6。

## 4. Task List

### Phase 1 — 后端三步端点

- [ ] **T1 记录段 replay 端点**（M：3-4 文件）
  - Description：`GET /api/retrospectives/replay`（登录，period 参数）聚合四源：时间线节点回传（`TimelineNode`+feedback）、行动钩子（003 载体）、条件账本变化（condition_checklist）、职业事件（`CareerEvent`）；输出 spec §4 结构 + `material_status`（ok/thin，阈值执行期定，建议 <3 条=thin）。
  - Acceptance：① 各源条数与 DB 对账一致；② 空时段 `items=[]` 且 `material_status=thin`；③ 零 LLM（无 AIOrchestrator 调用）。
  - Verify：`cd backend && py -3.13 -m pytest tests/test_retro_replay.py -q`；curl 8001 实测。
  - Files：`backend/app/services/retro_replay_service.py`（新）、`backend/app/api/retrospectives.py`、`backend/app/schemas/retrospective.py`、测试。
  - Deps：None（A 类 commit 为工作区前置）。

- [ ] **T2 反思段双我端点**（M：2-3 文件）
  - Description：`POST /api/retrospectives/review-draft`——SYSTEM_PROMPT 内置 skill §E3 双我机制与反方清单四问；输入=period+replay 摘要+可选 my_view；输出四段 JSON（my_view/reviewer_challenges[]/my_response/sharpest_challenge）+ `low_confidence`（material_status=thin 时置 true 且 prompt 要求"如实说明材料不足"）；限流复用 `RETROSPECTIVE_AI_DRAFT`；降级 503/504 同 `ai-draft` 范式。
  - Acceptance：① 四段字段齐全，`sharpest_challenge` 非空；② thin 材料时 `low_confidence=true` 且文案不编事实；③ 未登录 401、限流生效。
  - Verify：pytest（mock LLM：含 JSON 容错与兜底路径）+ 手工一次真调。
  - Files：`backend/app/services/retro_ai_service.py`（+函数）、`backend/app/api/retrospectives.py`、`schemas/retrospective.py`、测试。
  - Deps：T1。

- [ ] **T3 原则提炼端点**（M：2-3 文件）
  - Description：`POST /api/retrospectives/principle-draft`——输入=反思结论+可选 note；LLM 产出 1–2 条候选（text/trigger/next_action/needs_refine）；后端规则二次检测：无动作动词（"做/改/加/跑/写/核对/测试/提交"类）、长度 <8 或 >30 字、纯形容词黑名单（"细心/认真/努力"等）→ `needs_refine=true`。
  - Acceptance：① 正常输入返回候选；② 空话样例被标 `needs_refine=true`；③ 每时段原则总数校验入口（配合 T4 的 ≤3）。
  - Verify：pytest（含空话样例集）+ 手工。
  - Files：`backend/app/services/retro_ai_service.py`、`api/retrospectives.py`、测试。
  - Deps：T2。

### Phase 2 — 原则库

- [ ] **T4 principle 类型 + 落库约束**（S：3-4 文件，含迁移）
  - Description：`MemoryFactType` 加 `principle`（PG enum 迁移：Alembic `ALTER TYPE ... ADD VALUE`；迁移前实测生产 `alembic current`、单头自检）；`POST /api/user-memory` 增加约束——`fact_type=principle` 时必须 `confirmed=true` 且每用户每时段 ≤3 条（按 fact_key 前缀计数）；`fact_value` 存储格式见 spec §4。
  - Acceptance：① 迁移本地/演练环境通过且可逆有说明；② 未确认入库 422；③ 超 3 条 422；④ 既有 user-memory 测试不红。
  - Verify：pytest + `alembic upgrade head` 本地实测 + 迁移单头检查。
  - Files：`backend/app/models/user_memory.py`、`backend/alembic/versions/<new>.py`、`backend/app/schemas/user_memory.py`（如有）、`api/user_memory.py`、测试。
  - Deps：T3（语义衔接；实现可与 T2/T3 并行）。

### Checkpoint A（T1-T4 后）
- [ ] 后端全绿 + import 冒烟 + 迁移演练通过；replay 各源条数与 DB 对账结论记录。
- [ ] 方向席位过目：四段反思文案与 skill 双我机制一致（含"最尖锐反驳"必给）。

### Phase 3 — 前端与全链

- [ ] **T5 复盘页三段扩展 + 原则库块**（M：3-5 文件）
  - Description：`RetroAIPanel` 扩展为三步交互——①记录（replay 列表，thin 提示）②反思推演（四段展示，"最尖锐反驳"高亮）③提炼原则（候选卡片+可编辑+空话提示+确认入库）；复盘页加"我的原则库"块（列表/删除/反馈，复用 user-memory API）；375px 可用。
  - Acceptance：① 三步可独立操作；② needs_refine 未改写不能提交；③ 原则库增删生效；④ 无新依赖。
  - Verify：`cd frontend && npx tsc --noEmit && npx vitest run`；本地手测（真机 375px）。
  - Files：`frontend/components/retro-ai-panel.tsx`、`frontend/components/principle-library.tsx`（新）、`frontend/app/(app)/retrospectives/page.tsx`、`frontend/lib/api/*`、测试。
  - Deps：T4。

- [ ] **T6 注入断言 + 全链演练**（S：1-2 文件）
  - Description：断言 `build_context_prompt`（或 `_serialize_memory_fact`）输出含原则文本（穿到 prompt 文本层，防假绿）；本地全链：时段→replay→反思→提炼→确认入库→对话上下文可见。
  - Acceptance：① 注入断言绿；② 全链一次通过（记录失败点）；③ 原则删除后注入消失。
  - Verify：pytest + 手工全链 + 部署后 HTTPS 冒烟（绑特有断言）。
  - Files：测试文件、`docs/验收清单` 更新（方向席位）。
  - Deps：T5。

### Checkpoint B（T5-T6 后）
- [ ] 前端三绿 + 375px + 全链演练通过；部署冒烟通过；方向席位验收。

## 5. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| PG enum 迁移不可逆风险（`ADD VALUE` 不易回退） | 中 | 迁移前实测生产 `alembic current`；迁移脚本注明回退需手工处理；本地先演练 |
| LLM 输出格式漂移（四段 JSON） | 中 | 复用 `_parse_llm_json`/`_coerce_draft` 容错范式 + 兜底结构；负例测试覆盖 |
| 空话原则绕过检测 | 中 | 规则+LLM 双保险；needs_refine 前端强拦；样例集进 pytest |
| 反思文案变"评判用户" | 低 | prompt 纪律：双我是"照镜子"不是"审判"；文案复核（Checkpoint A 方向席位过目） |
| 复盘页在 A 类批次被改动 | 低 | 开工前 `git show <A类commit> --stat` 核复盘页改动面 |

## 6. Checkpoints 汇总
- Checkpoint A：后端全绿 + 迁移演练 + 文案语义过目。
- Checkpoint B：前端三绿 + 全链 + 部署冒烟 + 验收。

## 7. Open Questions
- 原则入 `fact_value` 的结构化分隔符格式是否需独立字段（现模型无 metadata 列；执行期若觉受限，可评估加 `JSONB meta` 列的迁移——本期先用分隔符，控范围）。
- 原则库是否需在 chat 侧显式展示"AI 记得你的原则"（记忆感 UI，003 范畴，本期不做）。
