# Tasks 003：AI 对话粘性三件套

> 依赖：plan.md 落点 + research.md R1-R8。实现顺序=杠杆序（记忆感→钩子→深链）。
> 纪律：只 add 本 feature 文件（工作区有并行线 250 条脏条目）；零迁移；三绿+pytest 全绿才准提交。

## Phase A 后端（杠杆 1+2：记忆感 + 行动钩子）

- [x] A1 `backend/app/config.py`：新增 `SITE_BASE_URL: str = ""`（空=推送深链行自动省略）
- [x] A2 `backend/app/services/sedimentation_service.py`：`build_sedimentation_block`（订阅/待回传/微行动/连击四段，逐段独立降级）；公开 `get_user_subscriptions` / `get_pending_feedback_nodes` 供钩子同源消费（A2 原则：待回传定义单点）
- [x] A3 `backend/app/services/action_hook_service.py`：`build_action_hooks`（域检测复用 `detect_data_intents`；timeline/announcements→订阅+回传钩子，微行动→打卡钩子，无沉淀→探索型；≤2 个；整段异常降级空表）
- [x] A4 `backend/app/schemas/chat.py`：`ActionHook{type,text,link}` + `SendMessageResponse.action_hooks` 可选字段
- [x] A5 `backend/app/services/chat_service.py`：`apply_sedimentation`（纯函数：块空⇒追加"无沉淀禁虚构"行；块非空⇒块+记忆感纪律）接在 user_context 后；返回前组钩子入 result 与 context_snapshot
- [x] A6 后端负例测试 `backend/tests/test_chat_stickiness_003.py`：无沉淀块空/有沉淀含考次名/已订阅无订阅钩子/待回传出回传钩子/异常降级空表/深链试探文案零断言词/深链容量硬闸/with_chat_link 两态

## Phase B 深链（杠杆 3：推送→对话）

- [x] B1 `backend/app/services/chat_deep_link.py`：`build_chat_deep_link(node, exam, kind, tone)`（prefill 模板按 tone 分级内聚本函数；≤40 字截断+link ≤500 硬闸）+ `with_chat_link(content, link)`（SITE_BASE_URL 空则原样）
- [x] B2 `backend/app/services/timeline_reminder.py`：`pick_template` 的 link 改走 B1；`_send_one` 的 Server酱 content 经 `with_chat_link`；ReminderDraft docstring 补记"唯一允许的追加=深链行"
- [x] B3 contract 同步：`contracts/notification-deeplink.md` 函数签名与实现一致（kind+tone 入参）

## Phase C 前端

- [x] C1 `frontend/lib/chat-deeplink.ts`：`readChatDeepLink(search)` 纯函数（prefill/skill 白名单解析）+ vitest
- [x] C2 `frontend/lib/api` 类型：SendMessageResponse 补 `action_hooks`
- [x] C3 `frontend/app/(app)/chat/page.tsx`：Suspense 包裹+useSearchParams 预填 input/skillHint（不自动发送）；回答气泡尾部渲染钩子胶囊按钮（点击 router.push）
- [x] C4 三绿：lint + vitest + build

## Phase D 度量（FR8）

- [x] D1 `docs/度量口径.md` 增补：对话→订阅转化 / 对话→回传转化 / 提醒深链点击率三口径（曝光=context_snapshot.action_hooks，点击=对话页 PV src=reminder）

## Phase E 部署（宪法 8）

- [ ] E1 提交：显式路径 add 本 feature 文件 → `git diff --cached --name-only` 核对 → commit
- [ ] E2 `bash tools/gp-preflight.sh <目标>` 四闸；ff 闸预期红（本地 54ab880 与生产 8ade9ca 平行分叉）→ `bash tools/gp-converge.sh <我的提交>` 只摘本提交
- [ ] E3 bundle→scp→`update_from_bundle.sh`（nohup 后台+轮询）；生产 .env 补 `SITE_BASE_URL=https://quxianglab.cn`
- [ ] E4 部署后验证：拓扑祖先核对+容器日志+site-packages 实证新模块+HTTPS 冒烟（记忆感/钩子/深链三件）+冒烟账号删除
