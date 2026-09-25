# Plan 010：人生设计随访实验——实施与推进计划

- **Created**: 2026-09-19｜**执行**: 执行会话（规格席位出计划，git 写不碰）
- **纪律**: 010 spec 是边界（≤2 文件/零迁移/零新端点/不碰前端）；本计划把锚点钉死到行级，执行会话照锚动刀，禁止任何"顺手"扩展。
- **窗口**: T1 必须在 **9/22 前**上产（冻结窗 9/23-10/2 零新增）。

## 0. 前置对账（执行会话开工第一件事）

- `git -C . status` 确认工作区干净、`git log --oneline -5` 找到 009 收敛批（含 339200c 等）已上产；
- 009 残留复核两项顺办（也属窗前允许项）：①vault 页/考公 tab DOM 级角标 Playwright 复核；②9/20 14:11 自动回流复查作业结果（读日志，不重跑爬虫）；
- 数字复测：`GET /api/user-memory` 确认当前用户记忆事实数为空或已知值（实验基线）。

## 1. T0（用户本人，今天，零代码）

- 生产站跑一次完整人生设计访谈；
- 挑 2-3 条原则 → `POST /api/user-memory`：`fact_type=behavior|goal`，`fact_key=interview_principle_1..n`，`fact_value="原则：…；场景：…；下回：…"`；
- `GET /api/user-memory` 核对入库（此为 T1 开发与验收的数据前提）。

## 2. T1（执行会话，单文件 ~15 行）

### 锚点（已核实，2026-09-19）

| 锚点 | 位置 | 用途 |
|---|---|---|
| 记忆提示词构造器（现成） | `backend/app/services/user_context_service.py:273` `build_context_prompt(db, user_id) -> str` | 直接复用，不重写 |
| 调用先例（照抄范式） | `backend/app/services/chat_service.py`（grep `build_context_prompt\|get_user_context`） | 注入方式与空态处理照抄 |
| 注入点①访谈 | `backend/app/services/life_design_service.py:78` `generate_vision_from_audit(db, user_id, audit_qa)`（:98-99 处 orchestrator.chat） | **主改**：user_prompt 前拼接记忆块 |
| 注入点②季度随访 | `backend/app/services/life_design_service.py:167` `generate_sprint_review(sprint_id)`（:199-200 处 chat） | 次改：经 sprint 取 user_id 后同样注入 |

### 改动契约

1. 仅改 `life_design_service.py` 一个文件；`from app.services.user_context_service import build_context_prompt`；
2. 两处注入统一格式：记忆块作为前缀段落 + 硬规则一句——"若以下记忆含该用户此前访谈沉淀的原则，开场或首个提问须自然引用其中一条；不得复述全文；不得编造记忆中没有的内容；记忆为空时不得提及记忆"；
3. **负例必须保持现状**：无任何 memory_facts 的用户 → 构造的 prompt 与现行为一致（空态不加任何"记忆"字样）；
4. 禁止：principle 类型、提炼 UI、新端点、前端、sprint 之外的模型改动。

### 验收锚点（看什么/什么算过）

1. `pytest`（backend 目录跑）全绿——1896 基线不回退；
2. 负例手测：无记忆用户调 `POST /api/life-design/vision`（或对应路由）→ 响应与改动前同构、无记忆引用、无报错；
3. 正例手测：T0 已存原则的账号再调 → 响应文本中**出现至少一条所存原则的关键词**且语义准确；
4. 部署按家规：gp-preflight 四闸 → bundle → scp → update_from_bundle.sh → `git show --stat` 验内容 → HTTPS 登录态冒烟绑本次特有断言（正例用户访谈引用原则）。

### commit 语义

`feat(010-t1): 人生设计访谈注入用户记忆事实（随访实验最小闭环）`——单独 commit，绝不与 009 复核件混提。

## 3. T2 / T2b（上产后，用户本人，同日）

- T2：跑第二次访谈 → 断言 AI 开场引用 ≥1 条原则且准确，留原话截图；
- T2b（必做对照组）：同一背景材料在 ChatGPT/豆包（开持久记忆）跑同款访谈 → 打平即"AI 记得你"无缺口，方向降级作品收尾；只有结构化台账联动的判断胜出才算立住。

## 4. 观察窗（T2 后 30 天）

- 判据：用户未经提醒**自发**完成第三次访谈 → 方向成立，后续按"嘴/手法则"逐功能接入记忆脊柱（复盘原则 006 先行）；
- 不成立 → 009 收尾已完成，产品停建，写 AAR 复盘文档。

## 5. 排期总览

| 日 | 动作 | 谁 |
|---|---|---|
| 9/19 晚 | T0 跑访谈+存原则 | 用户 |
| 9/20 | 009 两项复核 + T1 开发上产 + 冒烟 | 执行会话 |
| 9/21 | T2 + T2b 对照 | 用户 |
| 9/22 | 冻结窗前收口确认（工作区干净、台账更新） | 执行会话 |
| 9/23-10/2 | 冻结窗：零新增 | — |
| T2+30 天 | 观察窗判读 | 用户+规格席位 |
