# Quickstart & 验收 006：复盘方法论产品化（B8 · ai-project-fupan 集成）

> 验收总纪律：`verify-gate-at-fact-moment-principle` + constitution 8 条 + `docs/验收清单-2026-09-14.md` 总则。

## §1 开工前置

1. **A 类批次已 commit** + `bash tools/topology.sh` 对账；`git show <A类commit> --stat` 核复盘页相关改动面（theory: 复盘页不在 A 删除面，但跳转链被改过）。
2. **迁移前置**：实测生产 `alembic current` 作 down_revision；本地 `alembic upgrade head` 演练通过；确认单头。
3. **契约核对**：spec §4 数据契约 + plan §2 决策；发现漂移回填 spec。

## §2 本地实施与演练

```bash
cd backend && py -3.13 -m pytest tests/test_retro_replay.py tests/test_retro_review.py tests/test_retro_principle.py -q
py -3.13 -c "import app.api.retrospectives; print('IMPORT OK')"
cd frontend && npx tsc --noEmit && npx vitest run
```

**演练脚本**（T5/T6 完成后）：
1. 选含留痕时段 → 记录段条目与 DB 对账（各源一条记录一条展示）；
2. 点"反思推演" → 四段可见，"最尖锐反驳"高亮；
3. 提炼原则 → 候选可编辑 → 确认入库 → 原则库可见；
4. 打开 AI 对话（或直调 build_context_prompt）→ 原则文本出现；
5. 删除原则 → 注入消失。

## §3 负例清单（防假绿，进 CI 级脚本）

| # | 负例 | 断言位置 |
|---|---|---|
| N1 | 无留痕时段不编内容 | replay `material_status=thin`；反思 `low_confidence=true`；文案断言不含具体成就编造 |
| N2 | 空话原则被拦 | `needs_refine=true`（"要细心"样例集）且前端不可提交 |
| N3 | 未确认不入库 | 无 `confirmed=true` 时 422 |
| N4 | 每时段 >3 条被拦 | 第 4 条 422 |
| N5 | 注入穿下游 | prompt 文本层断言含原则；删除后断言不含 |
| N6 | 双我与既有草稿不串 | `ai-draft`/`draft` 行为不变（既有测试全绿） |

## §4 部署与冒烟（HTTPS）

1. 迁移在前（`alembic upgrade head` 于容器内，先备份）；`gp-preflight.sh` 四闸 → bundle→scp→`update_from_bundle.sh`；
2. 冒烟绑特有断言：登录态完成一次"记录→反思→提炼→入库→对话可见"全链；冒烟账号验证后删除；
3. 更新后必部署才勾账。

## §5 命名与实现漂移记录（执行时以代码为准）

- 反思/提炼的 LLM 调用复用 `retro_ai_service` 的容错解析范式（`_parse_llm_json`/`_coerce_draft`）；
- 限流名沿用 `rate_limits.RETROSPECTIVE_AI_DRAFT`（`api/retrospectives.py:81`）；
- 记忆注入链=`user_context_service.build_context_prompt`（被 `chat_service.py:201` 引用）；
- `MemoryFactType` 为 Python enum → PG enum，迁移用 `ALTER TYPE ... ADD VALUE`。

## §6 验收清单（方向席位逐条实测）

| # | 检查点 | 判据 | 锚点（规划时点已实测） |
|---|---|---|---|
| 1 | replay 聚合正确 | 四源条数与 DB 对账；thin 阈值生效 | `CareerEvent`（`retro_ai_service._build_context` 范式）、timeline feedback、action_hook、condition_checklist |
| 2 | 双我四段结构 | 字段齐全、"最尖锐反驳"必给、low_confidence 正确 | skill §E3 反方清单四问 |
| 3 | 空话闸 | 规则+LLM 双保险实测拦截样例 | plan D5 |
| 4 | 原则库落库/删除 | 确认后才入库；≤3/时段；删除生效 | `api/user_memory.py` CRUD |
| 5 | 注入复利 | `build_context_prompt` 含原则（文本层断言） | `user_context_service._serialize_memory_fact` |
| 6 | 迁移纪律 | 生产 `alembic current` 对账、单头、备份先于执行 | constitution 7 |
| 7 | 既有链路不破 | `ai-draft`/`draft`/`weekly-draft` 测试全绿 | `api/retrospectives.py:57-119` |
| 8 | 文案语义 | 双我=照镜子非审判；局限如实标注 | skill 边界（B 段） |

## §7 冲突面核对

- 复盘页/面板不在 A 类删除面（A2=上岸报告/导师评价；决策页跳转改动已随 7816ebc 落地）；实施前仍以 `git show` 实核为准。
- 与 005 交汇：本 spec 不触碰考试流程 tab 与 companion 组件（零重叠）；两者可并行实施（不同文件族）。
- 与执行会话撞车处置：同文件即停手报方向席位（历史教训）。