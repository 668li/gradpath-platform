# Research 003：AI 对话粘性三件套

> 探索方式：speckit 子代理因并发上限不可用（两次启动均被拒），改为主会话直接定向探索。全部结论带 file:line 实证。

## R1. 记忆感的落点：独立沉淀块 vs 扩 build_user_context

**Decision**: 新建 `sedimentation_service.build_sedimentation_block(db, user_id)`，在 `send_message` 组装 system prompt 时追加；**不**扩 `build_user_context`。

**Rationale**:
- 实证缺口：`build_user_context`（chat_service.py:116-345）聚合画像/测评/规划/技能树/条件账本/事件/决策/复盘/洞察，**不含** ExamSubscription/NodeFeedback/MicroActionPlan/StreakRecord——记忆感原材料根本没进上下文，"已聚合订阅/回传"的旧判断与代码不符（09-12 探索实证）。
- 新鲜度：订阅/回传是"刚做完就该被引用"的数据，`build_user_context` 有 300s 缓存（key=`user_context:{user_id}`，chat_service.py:127）——用户刚点完回传就来聊，缓存会给出滞后引用，管家感变穿帮感。沉淀块每轮实时查。
- 成本：4 组索引小查询（subscription join exam 1 次、待回传节点 1 次、active 微行动计划+当日任务 1 次、streak 1 次），无缓存必要；逐段 try/except 独立降级。

**Alternatives considered**:
- 扩 build_user_context：一处改动覆盖所有消费方（决策引擎等），但混入缓存滞后语义、且该函数已 230 行（趋势警惕）；否。
- 进 skill.inject_data 逐个加：数据型 skill 只有 2 个声明 covered_data_domains（announcement_interpreter.py:26、timeline_companion.py:32），salary/market 由通用 `run_data_search` 供给（data_search_service.py:388-423）根本不是 skill——逐 skill 加覆盖不全；否。

## R2. 记忆感纪律放哪：chat_service 统一层 vs 各 skill prompt

**Decision**: 统一层。`send_message` 中沉淀块非空时，在其后追加一段固定"记忆感纪律"文本（≤1 条引用、须与块原文一致、空块禁任何"你订阅过/你上次"回溯句式）。

**Rationale**: spec FR1 原文写"数据型 skill 的 prompt 加一条"，但按 R1 探索，salary/market 数据面无 skill 载体；统一层一次落点、全 skill（含 DefaultSkill）覆盖、负例测试一处可断言。属 spec 措辞的实现级修正，语义不变（数据型对话面）。

**LLM 幻觉的诚实边界**（宪法 1 落点）：prompt 纪律是软约束。确定性测试只能断言"块为空 ⇒ prompt 不含沉淀块"；LLM 是否编回溯句无法单测锁定，靠 quickstart 冒烟抽测（无沉淀新用户同问题人工核对）。这是本 feature 唯一无法测试锁死的面，如实记录。

## R3. 行动钩子：服务端模板 vs LLM 生成

**Decision**: 服务端模板拼装 `action_hook_service`，返回结构化 `[{type, text, link}]`，前端渲染按钮；不走 LLM。

**Rationale**:
- 零造假可测：钩子文案是代码常量+库数据插值，无幻觉面；"可执行/已做过"判定查真实库（订阅存在性 unique(user,exam)、待回传=已发提醒且无 NodeFeedback 记录、微行动活跃计划存在性）。
- 可用性：LLM 429/超时（免费模型分钟限流是常态，见免费 AI 记忆）不影响钩子——钩子在响应组装层，异常整段降级空表（spec FR7）。
- 交互质量：结构化按钮比让 LLM 在正文里写"你可以点击…"可靠，前端可点、可打点。

**Alternatives considered**:
- LLM 尾部生成：不可测、易编造、429 即消失；否。
- 纯前端按 skill 猜：前端无库数据，"已做过"判定不可能诚实；否。

**域映射初版**（实现时可调）：

| 域/状态 | 钩子 | link |
|---|---|---|
| timeline 域且未订阅当前 exam | "帮你盯 {exam.name} 的时间线，节点准时提醒" | `/civil-service?tab=timeline`（订阅按钮所在） |
| timeline 域且有已到达未回传节点 | "{node.title} 完成了吗？30 秒回传" | `/civil-service?tab=timeline&node={id}` |
| announcements 域 | 订阅钩子（同上） | 同上 |
| 有 active 微行动计划 | "第 {day} 天的 {task.title} 打卡了吗" | 微行动页 |
| 无任何沉淀 | 探索型钩子（测评/微行动入口） | 对应页 |
| 每轮 | 按优先级取前 2（spec FR7） | |

## R4. 深链设计：指向对话页 vs 保留时间线 tab

**Decision**: 节点提醒的 `Notification.link` 与 Server酱文案改指对话页 `/chat?prefill=<文案>&skill=timeline_companion&src=reminder&node=<id>`；`/civil-service?tab=timeline&node=` 不删（回传钩子仍指它）。

**Rationale**:
- US3 的"推一次、拉一次"闭环要求落点是对话（AI 接住上下文）；落时间线 tab 只完成"看"，不完成"问+回传"。
- 站内通知点击跳 link 已实现（notifications/page.tsx:115-118 `<Link href={n.link}>`），改 link 即通，零前端通知侧改动。
- prefill 只填输入框不自动发送（spec A4）：规避自动调 LLM 的意外消耗与未登录中途拦截面。
- 未登录：middleware.ts:115-120 已有 `/login?redirect=<pathname+search>` 完整回跳（query 保留），US5 现成。

**时间诚实闸**（宪法 4）：prefill 文案由 `build_chat_deep_link(node, exam, tone)` 生成，tone 直接复用 `pick_template` 已判定的 `ReminderTone`（timeline_reminder.py:125-181 的单点闸），tentative ⇒ 试探式措辞；负例测试断言打到最终 URL 解码后的 prefill 文案。

**Alternatives considered**:
- 双 link（站内→对话、Server酱→时间线）：两通道口径分裂，且 Server酱想点进对话还得从站内转；否。
- link 保留时间线 tab 不改：闭环断在第一步；否。

## R5. Server酱深链与 SITE_BASE_URL

**Decision**: `_send_one` 的 Server酱 content 追加一行 `进对话页直接问：{SITE_BASE_URL}{link}`；新增 settings 项 `SITE_BASE_URL`（生产 .env 填 `https://quxianglab.cn`）。

**Rationale**: 实证 `_send_one`（timeline_reminder.py:189-240）只发 `(title, content)`，push 内容无 URL；站内 Notification 有 link 字段（models/notification.py:34）但 Server酱用户在微信里，无绝对 URL 就断了闭环。grep `backend/app/core/config.py` 与 `push_notify.py` 无现成 BASE_URL 配置——需新增，属最小配置增量。Server酱 desp 支持 markdown 链接（现网文案为纯文本+句号结构，追加一行文本链接最稳，不赌渲染差异）。

## R6. 前端预填实现：useSearchParams + Suspense

**Decision**: chat/page.tsx 用 `useSearchParams()` 读 `prefill`/`skill`，`useEffect` 一次性写入 input/skillHint state；组件树以 `<Suspense>` 包裹防 Next 14 的 CSR bailout 构建错误。

**Rationale**: 实证 page.tsx 现无 searchParams 消费（grep 无 useSearchParams），但"点击填 input+预选 skill"的既有模式在页内已存在（page.tsx:72 starter prompts 复用同一 state 写入路径），预填只是多一个入口；skill=timeline_companion 与 `skillHint` state 直接对齐。Suspense 要求为 Next 14 App Router 已知约束（useSearchParams 必须 Suspense 边界，否则 next build 失败）。

**风险**: query 长度——prefill 文案为一句话（≤120 字），URL 总长 <500B，无风险；XSS——React 对插入 input value 的字符串自动转义，prefill 只进 input state 不进 dangerouslySetInnerHTML。

## R7. 打点与度量（FR8，P2）

**Decision**: 钩子当轮清单记入 `Message.context_snapshot["action_hooks"]`（Message 已有 JSONB context_snapshot，chat_service.py:523-527 先例）；深链带 `src=reminder&node=<id>`，对话页 PV 按参数可反查提醒点击；口径入 `docs/度量口径.md` 增补节。

**Rationale**: 零迁移；曝光（context_snapshot）与点击（src 参数）分离可算转化。不做独立埋点表——P2 从简，先跑通口径。

## R8. 与并行线/观察窗的冲突面检查

- 提醒行为实验观察窗至 09-18（行为设计记忆）：本 feature **不动** `firing_kinds`/配额/幂等判定，只动 link 指向与 Server酱文案尾行——判据（续做率）不受污染；深链点击是新增正向变量，观察窗内如需隔离可按 `src` 参数剔除。
- 002-crawler-foundation（并行线）：无共享文件；工作区现有未提交改动全在 crawler 域，本 feature 文件集与之零交集。
- timeline_service 返回原始字典非 VO 的旧坑（AI 数据层记忆）：`build_chat_deep_link` 的输入直接取 `pick_template` 的 `ReminderDraft`（结构化 dataclass，timeline_reminder.py:57-61），不走 timeline_service，不踩该坑。
