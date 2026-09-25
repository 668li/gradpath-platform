# Implementation Plan 004：考公公告季官方源监控与事件就绪

- **Spec**: `spec.md` ｜ **Branch**: deploy-rebased ｜ **窗口**: 9/23–10/2 → D-day 10/14
- **执行者须知**：本 spec 由执行会话实现；**交付时必须附验收证据包**（git show --stat/回归绿/pre-commit/生产实证/部署痕迹），验收清单见 `docs/验收清单-2026-09-14.md` §三。

## Technical Context

| 项 | 值 |
|---|---|
| 后端 | FastAPI（`backend/app`），Python 3.13，pytest 从 `backend` 目录跑；端口 8001 |
| 前端 | Next.js（`frontend/app`），端口 3000；考公中心=既有 `civil-service` 页/timeline 域 |
| 爬取工装 | curl_cffi + trafilatura（既有）；yaml 配置 + 纯函数 + 2 样本（002 范式）；低频、单页触发、WAF/403 如实记录 |
| 调度 | 进程内 APScheduler（复用 `_register_d2_reminder_job` 注册先例） |
| 存储 | alembic 单头；**复用** `official_announce` 归口 + `_fetch_log` 信任锚（002 交付）；新增表见 `data-model.md` |
| 通知 | 复用 Notification(type=reminder) 幂等/配额（001 FR2/FR4）；**不新增渠道**（09-14 决策） |
| 铁律 | 职位内容不解析不入库；无源不展示；事件必挂 evidence |

**NEEDS CLARIFICATION（→ research.md）**：
1. gov.cn 转登静态全文假设（探针 FR2 第一优先；本机搜索通道本轮不可用，未验证——执行期首任务）
2. 时效 SLA N 的标定方法（首周标定口径）
3. 与并行会话删除改动（mentors/outcome_report）的相交面——执行前 `tools/topology.sh` 对账 + 与执行会话确认 commit 已落地

## Constitution Check

| # | 宪法条 | 判定 | 依据 |
|---|---|---|---|
| 1 | 零造假 | ✅ | 全部展示走证据闸 FR-E1/E2/E1b；可信度+采集时间前置 |
| 2 | 定位红线 | ✅ | 事件+外链情报卡；职位库不复活、职位表不解析（FR4） |
| 3 | 合规爬取 | ✅ | 官方公开页+低频+单页触发；manual_paste 兜底；不绕 WAF |
| 4 | 时间诚实 | ✅ | OFFICIAL/PREDICTED/UNKNOWN 语义沿用 001；负例打到展示文案层（FR7） |
| 5 | 身份覆盖 | ⚠️→✅ | G1/G2 全国事件无身份分化（H10 已知）；广东线=省份键补位；G4 条件纳入学历+专业+应届键。本 spec 立项理由之一即补此缺口 |
| 6 | 推送纪律 | ✅ | 不新增渠道；Notification 沿用既有幂等/配额 |
| 7 | 工程纪律 | ✅ | 8001/3000；alembic 单头+生产 current 实测；pytest from backend；前端三绿 |
| 8 | 部署纪律 | ✅ | 禁 reset；gp-preflight 四闸；HTTPS 冒烟；冒烟账号即删 |

**无违宪项，无需 Complexity Tracking。**

## Phase 0 / Phase 1 产物（已生成）

- `research.md`：转登假设、事件 vs 入库、capture-then-publish、manual_paste 兜底、SLA 标定——决策与备选
- `data-model.md`：SourceWatch / ExamEvent / IntelCard + 复用实体与状态流转
- `contracts/announcement-events-api.md`：公开事件/情报卡读取 + admin manual_paste 写入
- `quickstart.md`：探针 runbook、本地全链演练、负例清单、SLA 度量、公告日彩排

## 实施次序（Phase 2 窗口 9/23–10/2，探针预算 ≤5 人日含 G1/G2+广东抽样）

1. **探针（第一优先，约 2 人日）**：转登栏目 5 组候选 URL 验证 → 结论落 research.md；失败分支=manual_paste 彩排（与《考公尖刀集》runbook 联调）。
2. 源清单 yaml + `SourceWatch` 表 + 迁移（alembic 单头自检）。
3. 指纹检测 job（日扫 + 窗口升档）→ `ExamEvent` 管道（幂等）。
4. 事件/情报卡 API + 考公中心挂载（时间线节点引用 + 事件流区）。
5. SLA 度量落库 + 公告季日报。
6. 负例测试进 CI 清单 + 前端三绿 + 生产冒烟。
7. FR8 G4 规则卡（✅09-19 拍板确定纳入）。
8. **10/14 前彩排**：manual_paste 值守全链 + 公告日值守排班表（30 分钟响应窗口）。

## Risks

| 风险 | 缓解 |
|---|---|
| 转登假设失败（H8 已预判） | manual_paste 值守兜底 + 专题子页探针覆盖（G2 子页大概率同陷 SPA 壳） |
| 短窗事件与日扫频率矛盾 | 窗口期检查频率升档配置化（FR3）；"捕获即上站"口径（H7） |
| 与并行会话改动相交 | 执行前 topology.sh 对账；显式路径 add；commit 前核 `git diff --cached` |
| 公告日实际日期漂移（近五年 4 次 10/14，1 次疫情推迟） | 日历侧按 10/14 备战、`PREDICTED` 标签；公告发布即硬更新 |
