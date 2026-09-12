# Research 001：时间线伴随 MVP 设计决策

## D1 日期诚实状态机
**Decision**: `ExamNode.date_status ∈ {OFFICIAL, PREDICTED, UNKNOWN}`，`planned_date` 仅在前两者非空；OFFICIAL 必填 `source_url+collected_at`，PREDICTED 必填 `predict_basis`（如"按 2026 国考公告节奏平移"）。
**Rationale**: 宪法 1/4；581 判例=无状态标签的推算值以事实面世。
**Alternatives**: 不存预测日期（否决：无日期则提醒无从排程，产品空转）；预测值不加标签仅注释（否决：UI/文案层拿不到状态，闸失效）。

## D2 断言/试探双类文案模板 + 单点闸
**Decision**: 文案模板库分 `assertive`（含"已发布/明天截止"）与 `tentative`（"预计/建议关注"）两类；选择器 `pick_template(node, kind)` 是唯一入口——kind==assertive ∧ node.date_status!=OFFICIAL → 强制降级为 tentative（或跳过）。负例测试断言到最终渲染字符串。
**Rationale**: 教训"负例测试须穿下游闸否则假绿"（信任锚轮）；闸在数据/服务层不算穿过。
**Alternatives**: 前端隐藏（否决：推送绕开前端）；靠 review 自觉（否决：无强制）。

## D3 调度载体：进程内 APScheduler
**Decision**: 在 `timeline_service.register_timeline_jobs()` 注册日扫 cron（凌晨 07:30 亚洲/上海时区），main.py startup 调用，完全复刻 `_register_d2_reminder_job` 先例。
**Rationale**: 节点日级精度足够；无 beat 容器锚点已证；复用开关（MICRO_ACTION_REMINDER_D2 同款 env gate，`TIMELINE_REMINDER_ENABLED` 默认开）。
**Alternatives**: Celery beat（不存在独立 beat，走 worker 定时=双栈复杂化，否决）。

## D4 幂等：DB 唯一约束而非代码判断
**Decision**: `timeline_reminders` 轻表（user_id, node_id, kind, sent_at）+ unique(user_id,node_id,kind)；写入撞约束=已发过，跳过。
**Rationale**: 多 worker/重启场景代码级 set 会漂；DB 约束是硬闸（flock 同思想）。

## D5 提前量表（提醒窗口）
**Decision**: 可配置默认表：公告 T-3+T-0；报名 首日+T-3+截止 T-1；缴费 截止 T-2；准考证 开放日；笔试 T-7/T-1；查分 开放日；调剂 窗口首周每日 1 条（配额内）；面试/体检/政审 通知后 T+1 跟进。材料清单挂节点卡而非提醒正文（防文案超配额）。
**Rationale**: 事件驱动供给（一年几十公告）下总量可控；"调剂窗口只开 1-2 天"是信息差价值峰值场景。

## D6 12 环节词表与暗知识 stage 对齐
**Decision**: `ExamNode.stage_key` 枚举十二值（announce/registration/payment/admission_ticket/written/score/adjustment/interview/medical/political/publicity/hire），提供映射表对齐 `CivilServiceDarkKnowledge.stage`（现为中文 stage），命中渲染经验卡（低可信标注照宪法）。
**Rationale**: 暗知识表自带 stage 字段，一套词表两处复用；FR9。
**Alternatives**: 各建各的（否决：双词表必然漂移）。

## D7 2026 事实数据获取 = 证据链闸（09-12 修订版，取代旧"人工标定"表述）
**Decision**: seed 不含任何日期常量；OFFICIAL 写入必须过 `require_evidence()`（真实 fetch 200+正文≥2KB+正文含该日期+证据行入库）或 manual_paste 通道（用户粘贴原文+官方 URL，校验粘贴文本含日期）。同日探针实证官方站是 SPA 壳/跳转页，**自动 fetch 通道对考公公告大概率不可行**（bm.scs.gov.cn 需 JS 渲染），故主路径=找政府域静态转登页，找不到=向用户要粘贴，再找不到=该节点保持 PREDICTED 并显示"暂无可核验来源"。
**Rationale**: 用户质询"带源 seed 是不是假数据"一针见血——若执行者是我，"人工标定"四字不设防就等于把 581（无验证的自申报当事实）重演一遍。教训入宪：**凡"标定/校对"类承诺，必须落成机器闸，落成闸的才有资格进计划**。
**Alternatives**: 模型记忆录入+事后抽查（否决，构造上允许造假）；Playwright 渲染抓 SPA（技术可行但引入重依赖且仍要人工核对文本，留 Phase 2 议）。

## D8 迁移落点
**Decision**: 新迁移 down_revision = 动手实测生产 `alembic current`（当前锚点 c8d4e6f2a9b1），单头自检进 M1 验收；表名前缀 `t_exam_*` 对齐现行 t_ 风格（notification 系无 t_ 前缀例外，但 t_ 为近年主流——以最新迁移文件实际风格为准）。
**Rationale**: 幻影 stamp 事故配方反向应用。

## D9 前端落点
**Decision**: 考公中心加第 4 个 tab"考试流程"；现有 `/timeline`（个人行动时间线）语义不同、不改名不复用；页面在 P2 收敛后的 nav 组里挂"考公情报"下。
**Rationale**: 避免与"timeline 提级"（行动线）撞语义；tab 内数据浏览公开、订阅按钮登录墙后跳 /login?redirect。
