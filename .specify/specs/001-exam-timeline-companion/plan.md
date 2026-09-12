# Implementation Plan 001：考公流程时间线伴随 MVP

**Spec**: [spec.md](./spec.md) ｜ **Constitution**: [.specify/memory/constitution.md](../../memory/constitution.md)
**窗口**: 2026-09-13 ~ 09-22（倒排"公告日预计锚点 10/14"——此锚点本身系推算惯例，官方公告为准，落证前不得对外表述为已确认日期）｜ 开工令 = 用户拍板 Q1

## Summary

新建"考次×12环节"三张表+订阅/回传两张小表，进程内 APScheduler 日扫生成节点提醒（站内 Notification + Server 酱，幂等+配额），前端考公中心加"考试流程"tab。核心设计是**日期诚实状态机**（OFFICIAL/PREDICTED/UNKNOWN）与**文案分级闸**（PREDICTED 永不出断言式提醒），并有穿到文案层的负例测试。全部基建复用现行栈，零新依赖。

## Technical Context

| 项 | 值 |
|---|---|
| Language | Python 3.11（生产容器）/ 本地 py -3.13；TypeScript |
| Frameworks | FastAPI + SQLAlchemy 2.0 + Alembic；Next.js 14 App Router |
| Datastore | PostgreSQL（prod db 容器）|
| Scheduling | APScheduler 进程内（backend 容器，无 beat 容器，锚点已证）|
| Push | 复用 `core/push_notify.send_serverchan` + `NotificationType.reminder` |
| Testing | pytest（backend 目录，基线 1878）+ vitest（基线 147）|
| 部署 | bundle→scp→update_from_bundle.sh；gp-preflight 四闸；禁 reset；冒烟走 https://quxianglab.cn |

**NEEDS CLARIFICATION**：无（全部在 research.md 有 Decision/Rationale）。

## Constitution Check

| 宪 | 判定 | 说明 |
|---|---|---|
| 1 零造假 | PASS | 每节点 source_url/采集时间/状态标签入库；2026 人工标定官方原文 |
| 2 定位红线 | PASS | 本 feature 即信息差伴随脊柱；不触职位/判定漏斗 |
| 3 合规爬取 | PASS | 本期不新增爬取（数据人工标定，公告自动捕获在 Phase 2） |
| 4 时间诚实 | PASS | 状态机+文案分级闸+负例测试穿文案层（FR3） |
| 5 身份覆盖 | PASS | 订阅以身份包为过滤面（国考/省考），不锁单一赛道 |
| 6 推送纪律 | PASS | 幂等键+INFO 配额沿用现行（FR2/FR4） |
| 7 工程纪律 | PASS | down_revision 实证生产 current；三绿门槛 |
| 8 部署纪律 | PASS | converge+preflight 已趟熟 |

**无违宪项，无需 Complexity Tracking。**

## Project Structure

```
backend/app/
  models/exam_timeline.py            # Exam/ExamNode/ExamSubscription/NodeFeedback
  services/timeline_service.py       # 查询/订阅/回传 + register_timeline_jobs()
  services/timeline_reminder.py      # 日扫 job、幂等、文案模板闸
  api/exam_timeline.py               # prefix=/api/civil-service/timeline
  schemas/exam_timeline.py           # VO（对齐现行 response_model 风格）
  alembic/versions/<new>             # down_revision=生产实测 current
backend/tests/test_exam_timeline_*.py # 含负例: test_predicted_never_assertive_reminder
frontend/app/(app)/civil-service/     # 新 tab "考试流程" + components/timeline/*
docs/度量口径.md                      # 增补 条件完成率/回传率 定义
```

## Milestones（对应 spec 验收）

- **M1 数据层**（9/13–9/14）：模型+迁移+**证据链闸**（require_evidence，D7 修订版）+seed 脚本（**零日期常量**；骨架+2027 PREDICTED；2026 日期仅经 fetch 证据或用户粘贴通道落库，取不到即保持预测态）。验收含"无证据 OFFICIAL=0 行"SQL 断言+坏输入三拒。取源前置任务：15 分钟找政府域 2026 公告静态转登页；找不到→向用户要粘贴。
- **M2 API**（9/15–9/16）：contracts 全端点+测试（含 422 断言、幂等）。
- **M3 提醒引擎**（9/17–9/19）：日扫 job+分级闸+配额；**负例测试先行**。
- **M4 前端**（9/20–9/21）：时间线 tab+订阅+回传 UI。
- **M5 全链+上产**（9/22）：E2E（调时→job→实收）、三绿、preflight、converge 部署、生产 HTTPS 冒烟、冒烟账号删除、记忆/PROGRESS 落账。

## 关键风险与对策（本 feature 特有）

1. **预测冒充事实**：文案闸在函数级单点（模板选择器），负例测试穿到底；代码评审 grep 断言式措辞清单（"截止/已发布/明天"）仅允许 OFFICIAL 分支。
2. **提醒风暴**：幂等唯一键在 DB 层（不只是代码判断）；启动注册沿用 d2 先例防重。
3. **迁移撞链**：动手前实测生产 current；单头自检进 preflight 第 4 闸复核。
4. **并行会话撞车**：开工前跑 topology.sh；前端只加 tab/组件，不动他人正在改的决策/职位相关文件。

## Phase 2+ 衔接（不在本期范围）

官方源自动捕获（official_announce 归口）→ `official_announce_id` 回填 OFFICIAL+推送；身份过滤"相关集"（壁垒验收）；每日一报。接口已在 FR10 留位。
