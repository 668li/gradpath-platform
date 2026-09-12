# Quickstart 001：时间线伴随 MVP 验证指南

前置：仓库 `D:\职业规划\职业规划`；本地后端 8001、前端 3000；`py -3.13`；Mimosa 拦截本机 httpx 冒烟 → 后端脚本冒烟走 TestClient，网络验证走服务器 curl/HTTPS（教训已录）。

## 1. 起环境与建数据（M1 验收）

```bash
cd backend && py -3.13 -m alembic current        # 记下 current，新迁移 down_revision 必须接它（禁幻影 stamp）
# 写迁移后：
py -3.13 -m alembic heads                        # 必须单头
py -3.13 -m alembic upgrade head && py -3.13 -m alembic downgrade -1 && py -3.13 -m alembic upgrade head
py -3.13 -m app.seed.seed_exam_timeline            # 幂等骨架（零日期）；跑两遍计数不变
py -3.13 -m app.seed.seed_exam_timeline --proposal app/seed/data/guokao_2026_evidence_proposals.json  # 提案逐条运行时重验
```
断言（证据闸版）：① seed 跑完，**无 evidence_id 的 OFFICIAL 行数必须=0**（SQL 直查）；② 国考 2027 全节点 `UNKNOWN⇒日期空`；③ 负例：向 seed 手喂"有日期无 source/壳页 URL/正文不含日期的 URL"三种坏输入 → 全部拒写并以 PREDICTED/UNKNOWN 落库；④ manual_paste 通道用你粘贴的公告原文测一条真 OFFICIAL。2026 节点允许"暂无可核验来源"的 PREDICTED 形态上线——**这不是失败，造假才是**。

## 2. API 冒烟（M2）

```bash
py -3.13 -m pytest tests/test_exam_timeline_api.py -q          # 含 422/409/404 负例
# TestClient（Mimosa 友好）: 订阅→me→feedback 闭环；跨考回传 404。
```

## 3. 提醒引擎与诚实闸（M3，宪法 4 判卷）

```bash
py -3.13 -m pytest tests/test_timeline_reminder.py -q
```
必含三个测试（名字可追溯宪法条款）：
1. `test_predicted_node_never_assertive_copy`：构造 PREDICTED 节点、时间窗命中 → 断言**最终渲染字符串**不含"已发布/明天/截止"断言词表，仅试探词。
2. `test_idempotent_reminder_log`：job 连跑两次 → TimelineReminderLog 每 (user,node,kind) 恰 1 行。
3. `test_info_quota_respected`：当日已 3 条 INFO → 新试探提醒不落 push（站内 Notification 仍记）。

手动：把某测试节点 `planned_date` 改成明天 → 跑 job → 服务器 Server 酱**实收**一条试探句（`ssh gradpath` 环境或本地 .env 配好 key）。

## 4. 前端（M4）

```bash
cd frontend && npx vitest run && npm run build
```
走查：考公中心"考试流程"tab → 时间轴/下一节点高亮/预测标签肉眼可见/官方直链新窗口/订阅登录墙跳转/反馈三态可点。

## 5. E2E + 上产（M5）

1. 全链：注册（@example.com）→订阅 guokao-2027→回传 done→`/me` progress 变化。
2. `bash tools/topology.sh` → 四闸语义确认；commit 显式路径+暂存清单核对（共享 worktree 纪律）。
3. `bash tools/gp-converge.sh <sha>` → bundle → `gp-preflight`（若脚本未在生产树则手动四闸：ff/磁盘/镜像/phantom stamp）→ scp → nohup update_from_bundle → **grep 全日志"更新完成"**（tail -3 会错过，本轮已踩）。
4. 生产 HTTPS 冒烟（80 已 301）：
   - `curl -sk --resolve quxianglab.cn:443:127.0.0.1 https://quxianglab.cn/api/civil-service/timeline/exams` 200+带源
   - 时间线页 200；提醒 job 开关 env 生效证据（backend 日志一行）。
5. 冒烟账号删除+复核计数恢复。
6. 落账：计划书 Phase1 行销账、PROGRESS/记忆/承诺台账（新挂账若有）。

## 通过判据 = spec §5 五条全绿；任一负例假绿 = 回炉。
