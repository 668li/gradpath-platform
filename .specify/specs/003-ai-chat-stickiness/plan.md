# Implementation Plan 003：AI 对话粘性三件套（记忆感 · 行动钩子 · 推送对话打通）

**Spec**: [spec.md](./spec.md) ｜ **Constitution**: [.specify/memory/constitution.md](../../memory/constitution.md)
**窗口**: 2026-09-13 ~ 09-18（提醒行为实验观察窗至 09-18，本 feature 不动提醒判定逻辑，互不干扰）｜ 开工令 = 用户拍板"按这个顺序做"

## Summary

零迁移改造：把已有管道接成闭环。① 新增**沉淀摘要**服务（订阅/节点回传/微行动/连击，实时查、逐段降级）注入 system prompt + 统一"记忆感纪律"prompt 段（无沉淀禁回溯句式，负例测试）；② 新增 **action_hook 服务**（域→钩子映射表驱动，三态诚实：可执行/已做过/降级），以 `SendMessageResponse.action_hooks` 可选字段返回，前端渲染按钮；③ 节点提醒深链统一函数 `build_chat_deep_link`（tone 判定复用 `pick_template`，PREDICTED 试探式），站内 `Notification.link` 改指对话页、Server 酱文案追加链接行（新增 `SITE_BASE_URL` 配置），前端对话页 `useSearchParams` 预填（不自动发送）。全程复用现行栈，无新表、无新依赖。

## Technical Context

| 项 | 值 |
|---|---|
| Language | Python 3.11（生产容器）/ 本地 py -3.13；TypeScript |
| Frameworks | FastAPI + SQLAlchemy 2.0（零 Alembic 迁移）；Next.js 14 App Router |
| Datastore | PostgreSQL（prod db 容器）——只读复用现有表 |
| 对话链路 | `chat_service.send_message`（backend/app/services/chat_service.py:348）；skill 匹配→`build_system_prompt`→`inject_data`【专有数据】→`run_data_search`（announcements/timeline/salary/market 四域）→LLM（BYOK）→`parse_response` |
| 沉淀数据面 | ExamSubscription/NodeFeedback（models/exam_timeline.py:198,219）、MicroActionPlan/Task（models/micro_action.py:17,41）、StreakRecord（models/streak.py）；**现状缺口：四者均不在 build_user_context（chat_service.py:116）内** |
| 提醒管道 | `timeline_reminder.pick_template`（D2 分级闸，link 现指 `/civil-service?tab=timeline&node=`）→ `_send_one`（幂等 unique(user,node,kind)→Notification(link)→send_serverchan(title,content)，**Server酱文案现不带 URL**） |
| 前端 | 对话页 `frontend/app/(app)/chat/page.tsx`（input/skillHint state 已有"starter 点击填入"先例，无 useSearchParams）；通知页 `n.link`→`<Link href>` 已实现跳转；登录守卫 middleware.ts `/login?redirect=<含search路径>` 回跳现成 |
| Testing | pytest（backend 目录）+ vitest；负例测试穿最终文案/URL |
| 部署 | bundle→scp→update_from_bundle.sh；gp-preflight 四闸；禁 reset；冒烟走 https://quxianglab.cn |

**NEEDS CLARIFICATION**：无（全部在 research.md 有 Decision/Rationale）。

## Constitution Check

| 宪 | 判定 | 说明 |
|---|---|---|
| 1 零造假 | PASS | 沉淀引用只许来自【用户沉淀】块原文；块为空时 prompt 不含该块（确定性负例）+"无沉淀禁回溯句式"纪律；钩子"可执行/已做过"判定查真实库，不得指向不存在对象（spec FR1/FR3） |
| 2 定位红线 | PASS | 纯对话面闭环，不新增数据域/爬取/判定漏斗；通用对话能力明确不碰（spec §4） |
| 3 合规爬取 | PASS | 零新增爬取 |
| 4 时间诚实 | PASS | 深链预填文案由 `build_chat_deep_link` 统一生成，tone 复用 `pick_template` 判定（PREDICTED⇒试探式）；负例测试断言打到最终 URL 的 prefill 文案与 Server 酱文案（spec FR6） |
| 5 身份覆盖 | PASS | 沉淀素材天然覆盖身份面：考公=订阅/节点回传，考研/就业=微行动/连击/CareerPlan 进度（已在画像）；探索型钩子不锁赛道 |
| 6 推送纪律 | PASS | 配额/幂等/判定逻辑零改动；仅 link 指向变更 + Server酱文案追加链接行；幂等键不变 |
| 7 工程纪律 | PASS | 零迁移；pytest+三绿；端口 8001/3000 |
| 8 部署纪律 | PASS | preflight 四闸+HTTPS 冒烟；冒烟账号验证后删除 |

**无违宪项，无需 Complexity Tracking。**

## Project Structure

```
backend/app/
  services/
    sedimentation_service.py        # 新：沉淀摘要（订阅/回传/微行动/连击，逐段降级）
    action_hook_service.py          # 新：域→钩子映射+三态判定（≤2 个/轮，异常降级空表）
    chat_deep_link.py               # 新：build_chat_deep_link 统一深链生成（tone 规则内聚）
    chat_service.py                 # 改：send_message 组装沉淀块+纪律段+action_hooks；
                                    #     build_user_context 不动（缓存语义保真）
    timeline_reminder.py            # 改：draft.link 走 build_chat_deep_link；Server酱文案追加链接行
  core/config.py                    # 改：新增 SITE_BASE_URL（Server酱深链绝对 URL 用）
  schemas/chat.py                   # 改：SendMessageResponse.action_hooks 可选字段 + ActionHook
frontend/app/(app)/chat/page.tsx    # 改：useSearchParams 读 prefill/skill 预填（Suspense 包裹，
                                    #     不自动发送）；action_hooks 渲染为胶囊按钮
frontend/lib/api/...               # 改：SendMessageResponse 类型补 action_hooks
tests/                             # 改：负例（无沉淀禁回溯/PREDICTED 试探文案/降级无钩子）
```

## 关键设计落点（与 spec FR 对应）

- **FR1 记忆感**：`sedimentation_service.build_sedimentation_block(db, user_id)` 每轮实时组块（4 组索引小查询，逐段 try/except）；`send_message` 在 skill.build_system_prompt 之后追加【用户沉淀】块；块非空时追加统一"记忆感纪律"段（≤1 条引用、必须与块原文一致、空块禁回溯）。不进 `build_user_context` 的 300s 缓存——"刚回传就引用"的新鲜度优先（research D1）。
- **FR2/FR3/FR7 行动钩子**：`action_hook_service.build_action_hooks(db, user_id, skill, content)` 在 send_message 返回前调用，与 inject_data 同 session 同口径（spec A2）；域映射：timeline→订阅钩子（未订阅该 exam）/回传钩子（有到达窗口未回传节点）、announcements→订阅钩子、micro_action 活跃计划→打卡/回传钩子、无沉淀→探索型钩子；≤2 个；整段 try/except 降级空表。
- **FR4/FR5/FR6 推送→对话**：`build_chat_deep_link(node, exam, tone)` 产 `/chat?prefill=<urlencode>&skill=timeline_companion&src=reminder&node=<id>`；`pick_template` 的 link 改走此函数；`_send_one` 的 Server酱 content 追加 `详情进对话页：{SITE_BASE_URL}{link}` 行；对话页 `useSearchParams` 预填 input（Suspense 包裹防 CSR bailout）+ preselect timeline_companion；未登录走 middleware 既有 `/login?redirect=` 回跳。
- **FR8 度量**：钩子当轮清单记入 `Message.context_snapshot["action_hooks"]`；深链带 `src=reminder&node=` 可从对话页 PV 反查点击；口径写入 `docs/度量口径.md` 增补节。
