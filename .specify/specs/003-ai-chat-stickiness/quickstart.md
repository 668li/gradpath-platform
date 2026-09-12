# Quickstart 003：AI 对话粘性三件套 验证指南

> 前置：后端 8001（pytest 从 backend 目录跑）、前端 3000；测试邮箱用 example.com（.test.local 被拒）；冒烟账号验证完必删。

## 1. 单元/负例测试（pytest，确定性面）

```bash
cd backend && pytest tests/ -k "sedimentation or action_hook or chat_deep_link" -x -q
```

必须覆盖的负例（对应 spec §5）：

| 测试 | 断言 |
|---|---|
| 无沉淀用户 | `build_sedimentation_block` 返回空 ⇒ 组装后的 system prompt **不含**【用户沉淀】块与记忆感纪律段（R2 确定性面） |
| 钩子三态 | 已订阅 ⇒ 无 subscribe_timeline；无待回传 ⇒ 无 feedback_node；≤2 个/轮 |
| 降级 | 钩子服务抛异常 ⇒ `action_hooks=null` 且回答正文正常返回 |
| 时间诚实 | PREDICTED 节点深链 prefill 解码后不命中 ASSERTIVE_WORDS；Server酱 content 含 `{SITE_BASE_URL}` 绝对 URL；prefill>100 字被截断且 link ≤500 字符 |

## 2. 记忆感 + 钩子端到端（本地）

```bash
# 造沉淀数据（一个测试号上）：订阅国考2027 → 节点回传 done → 建微行动计划 → 完成一次任务出连击
# 1) 起 8001 后登录测试号，在考公中心订阅 + 回传
# 2) 起 3000 进对话页，问：「国考报名什么时候截止？」
```

预期：
- 回答自然引用沉淀（如"你已订阅国考 2027…"），内容与库一致；
- 回答气泡尾部出现 ≤2 个胶囊钩子按钮，点击跳转正确（未订阅钩子/回传钩子按状态出现）。
- **负例人工核对**：换全新注册号同问题 ⇒ 回答无任何"你订阅过/你上次"句式，钩子为探索型（R2 承认的 LLM 软约束面靠此抽测）。

## 3. 推送→对话闭环（深链）

```bash
# 服务器侧（或本地 TestClient）触发一次节点提醒：
cd backend && python -c "
from app.database import SessionLocal
from app.services import timeline_reminder as tr
db = SessionLocal()
print(tr.send_timeline_reminders(db))  # 观察窗口期内调到 firing 节点，或临时构造测试节点
"
# 冒烟走 HTTPS 生产时：ssh gradpath 检查最新 Notification.link
ssh gradpath "docker exec <db容器> psql -U <user> -c \"select link from notifications where type='reminder' order by created_at desc limit 1;\""
```

预期：
- 站内：通知中心点击该提醒 ⇒ 落对话页、输入框已预填节点文案、skill 预选 timeline_companion、**未自动发送**；
- 未登录点深链 ⇒ `/login?redirect=<原样含query>` 登录后回到对话页且预填仍在（middleware.ts 现成回跳，验证 query 未丢）；
- Server酱实收（assertive 或配额内）⇒ 文案尾部含 `https://quxianglab.cn/chat?...` 可点；
- PREDICTED 节点同日触发 ⇒ 深链文案与推送文案均为试探式（负例测试 §1 已锁，此处人工复核实收文案）。

## 4. 回归与三绿

```bash
cd backend && pytest -q          # 基线 1902+ 全绿
cd frontend && npm run lint && npx vitest run && npm run build   # 三绿
```

## 5. 生产冒烟（部署后，gp-preflight 四闸先行）

1. HTTPS 冒烟：`https://quxianglab.cn` 登录冒烟号 → 重复 §2 §3 抽测；
2. 检查生产 settings 有 `SITE_BASE_URL=https://quxianglab.cn`；
3. 冒烟号订阅/回传数据 + 冒烟账号删除；
4. 北极星口径：`docs/度量口径.md` 增补节已更新（对话→订阅转化、对话→回传转化、提醒深链点击率三定义）。
