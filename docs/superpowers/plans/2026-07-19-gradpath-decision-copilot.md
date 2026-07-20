# GradPath 决策副驾驶 + AI 长期记忆 + 数据飞轮 优化计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GradPath 从"功能堆砌型平台"重塑为"决策副驾驶平台"——构建用户长期记忆、决策飞轮、暗知识主动推送、AI 个性化、模块数据流闭环五大护城河能力。

**Architecture:** 在现有 FastAPI + Next.js 架构基础上，新增 4 张数据表（user_memory_facts、user_onboardings、decision_review_queue、dark_knowledge_push_log）作为数据基础设施；新增 5 个服务层模块（user_context/user_memory/onboarding/decision_pulse/dark_knowledge_push）；新增 5 个 API 模块（通过 auto_discover_routers 自动注册）；前端新增 Onboarding 页面 + 决策副驾驶看板组件，改造 Dashboard 为"决策副驾驶"主面板。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (Mapped) + PostgreSQL/SQLite 双兼容 + Redis + JWT + MCP + WebSocket；Next.js 14 (App Router) + TypeScript + Tailwind + Zustand + Zod + Recharts；GLM-4 LLM via httpx。

---

## 文件结构

### 后端新增（23 个）

**Models（4 个）**
- `backend/app/models/user_memory.py` — UserMemoryFact 模型
- `backend/app/models/onboarding.py` — UserOnboarding 模型
- `backend/app/models/decision_review.py` — DecisionReviewQueue 模型
- `backend/app/models/dark_knowledge_push.py` — DarkKnowledgePushLog 模型

**Services（5 个）**
- `backend/app/services/user_context_service.py` — 用户上下文聚合（career_profile + onboarding + memory_facts + recent_decisions）
- `backend/app/services/user_memory_service.py` — 记忆提取/检索/反馈（调用 LLM 抽取结构化事实）
- `backend/app/services/onboarding_service.py` — 5 分钟职业诊断
- `backend/app/services/decision_pulse_service.py` — 决策副驾驶看板数据聚合
- `backend/app/services/dark_knowledge_push_service.py` — 暗知识主动推送

**API（5 个，自动注册）**
- `backend/app/api/user_context.py` — GET /api/user-context
- `backend/app/api/user_memory.py` — GET/POST/DELETE /api/user-memory
- `backend/app/api/onboarding.py` — GET/POST /api/onboarding
- `backend/app/api/decision_pulse.py` — GET /api/decision-pulse
- `backend/app/api/dark_knowledge_push.py` — GET/POST /api/dark-knowledge-push

**Tests（5 个）**
- `backend/tests/test_user_memory_service.py`
- `backend/tests/test_onboarding_service.py`
- `backend/tests/test_decision_pulse_service.py`
- `backend/tests/test_dark_knowledge_push_service.py`
- `backend/tests/test_user_context_service.py`

### 后端修改（9 个）
- `backend/app/models/__init__.py` — 注册 4 个新模型
- `backend/app/api/ai_agent.py` — 注入用户上下文（user_context_service）
- `backend/app/api/ai_enhanced.py` — 3 段式可解释输出 + 注入用户上下文
- `backend/app/api/decisions.py` — 创建决策时自动 schedule_review
- `backend/app/api/outcome_report.py` — 提交后异步生成经验贴
- `backend/app/services/experience_post_service.py` — 新增 create_from_outcome_report()
- `backend/app/services/decision_journal_service.py` — 复用决策回顾逻辑
- `backend/app/services/ai_service.py` — 新增 extract_memory_facts() / explain_3_section()
- `backend/app/core/scheduler.py` — 新增决策回顾到期推送定时任务

### 前端新增（11 个）
- `frontend/lib/api/decision-copilot.ts` — 决策副驾驶 API client
- `frontend/types/decision-copilot.ts` — 类型定义
- `frontend/app/(app)/onboarding/page.tsx` — 首次诊断页面
- `frontend/components/decision-pulse/overview-card.tsx` — 决策总览
- `frontend/components/decision-pulse/active-decisions.tsx` — 进行中决策
- `frontend/components/decision-pulse/review-queue.tsx` — 待回顾决策
- `frontend/components/decision-pulse/dark-knowledge-feed.tsx` — 暗知识推送流
- `frontend/components/decision-pulse/memory-facts.tsx` — AI 记忆面板
- `frontend/components/decision-pulse/index.tsx` — 看板容器
- `frontend/stores/onboarding.ts` — Onboarding 状态
- `frontend/stores/decision-pulse.ts` — 看板状态

### 前端修改（10 个）
- `frontend/lib/api/index.ts` — 导出 decision-copilot API
- `frontend/types/index.ts` — 导出决策副驾驶类型
- `frontend/app/(app)/layout.tsx` — 检测 onboarding 状态
- `frontend/app/(app)/dashboard/page.tsx` — 改造为决策副驾驶看板
- `frontend/components/nav.tsx` — 新增"决策副驾驶"入口
- `frontend/stores/auth.ts` — user.onboarding_completed 字段
- `frontend/types/user.ts` — UserResponse 新增 onboarding_completed
- `frontend/components/onboarding-dialog.tsx` — Onboarding 引导弹窗
- `frontend/app/(app)/decisions/page.tsx` — 决策列表增强
- `frontend/app/(app)/outcome-reports/submit/page.tsx` — 提交后跳转到看板

---

## Task 列表

### Phase A：数据基础设施

#### Task 1: UserMemoryFact 模型
- 创建 `backend/app/models/user_memory.py`：UserMemoryFact（id, user_id, fact_type, fact_key, fact_value, confidence, source, conversation_id, is_active, created_at, updated_at, last_used_at, use_count）
- 在 `backend/app/models/__init__.py` 注册
- 测试：SQLAlchemy metadata 可创建表

#### Task 2: UserOnboarding 模型
- 创建 `backend/app/models/onboarding.py`：UserOnboarding（id, user_id, current_stage, target_direction, target_industry, self_assessment, ai_diagnosis, recommended_path, completed_at）
- 注册 + 测试

#### Task 3: DecisionReviewQueue 模型
- 创建 `backend/app/models/decision_review.py`：DecisionReviewQueue（id, user_id, decision_id, scheduled_at, status, completed_at, ai_review_result）
- 注册 + 测试

#### Task 4: DarkKnowledgePushLog 模型
- 创建 `backend/app/models/dark_knowledge_push.py`：DarkKnowledgePushLog（id, user_id, dark_knowledge_id, stage, pushed_at, read_at, feedback）
- 注册 + 测试

#### Task 5: 建表验证
- 运行 pytest 全套测试确保新模型无冲突
- 运行 `python -c "from app.database import Base; Base.metadata.create_all(...)"`

### Phase B：核心服务层

#### Task 6: user_context_service
- `get_user_context(db, user_id) -> UserContext`：聚合 career_profile + onboarding + memory_facts（top 10） + recent_decisions + recent_outcome_reports
- 测试：mock 数据，验证聚合结果

#### Task 7: user_memory_service
- `extract_memory_facts(db, user_id, conversation_id, messages)`：调用 LLM 抽取结构化事实
- `get_user_memory(db, user_id, fact_type=None)`：检索事实
- `update_memory_feedback(db, fact_id, feedback)`：用户反馈
- 测试

#### Task 8: onboarding_service
- `create_onboarding(db, user_id, payload)`：保存诊断答案
- `generate_diagnosis(db, onboarding_id)`：调用 LLM 生成诊断 + 推荐路径
- `get_onboarding(db, user_id)`：查询
- 测试

#### Task 9: decision_pulse_service
- `get_pulse_overview(db, user_id)`：总览数据（决策数、准确率、记忆数、暗知识数）
- `get_active_decisions(db, user_id)`：进行中决策
- `get_review_queue(db, user_id)`：待回顾决策
- `get_dark_knowledge_feed(db, user_id)`：暗知识推送流
- 测试

#### Task 10: dark_knowledge_push_service
- `push_for_user(db, user_id, stage)`：根据用户阶段推送暗知识
- `mark_read(db, log_id)`：标记已读
- `record_feedback(db, log_id, feedback)`：记录反馈
- 测试

### Phase C：API 端点层

#### Task 11: 新增 5 个 API 模块
- user_context.py / user_memory.py / onboarding.py / decision_pulse.py / dark_knowledge_push.py
- 均含认证依赖、参数校验、限流

#### Task 12: 修改 ai_agent.py / ai_enhanced.py / chat.py
- 注入用户上下文到 system prompt
- AI 端点输出改为 3 段式：核心建议 / 依据 / 行动项

#### Task 13: 修改 decisions.py 自动 schedule_review
- 创建决策时自动创建 DecisionReviewQueue（基于 decision.review_date）

#### Task 14: 上岸报告 → 经验贴自动转化
- experience_post_service.create_from_outcome_report()
- outcome_report submit 端点：提交后异步生成经验贴草稿

### Phase D：前端实现

#### Task 15: 前端 API client + 类型定义
- decision-copilot.ts API client
- decision-copilot.ts 类型定义
- 在 index.ts 导出

#### Task 16: Onboarding 页面
- 首次登录检测 → 跳转 Onboarding
- 5 分钟诊断流程（4 步：基本信息 / 目标方向 / 自我评估 / 提交）

#### Task 17: 决策副驾驶看板组件
- 6 个组件：overview / active-decisions / review-queue / dark-knowledge-feed / memory-facts / index
- 改造 Dashboard 为决策副驾驶看板

### Phase E：回归验证

#### Task 18: 全量回归测试
- 后端 pytest 全套
- 前端 tsc --noEmit
- 运行时验证（关键端点 + SSR 页面）
