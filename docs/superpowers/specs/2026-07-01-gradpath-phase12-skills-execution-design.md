# GradPath Phase 12 设计：更多 Skills + 规划执行追踪

## 概述

Phase 12 聚焦两个子模块：
- **B2**：新增 2 个 Skills（考研规划 + 职业转型），扩展 AI 管家能力覆盖面
- **B3**：规划执行追踪，包含里程碑执行日志 + 到期提醒（按需计算，无需后台任务）

B1（外部搜索集成）延后，因需第三方 API 密钥配置。

## B2：新增 Skills

### 考研规划 Skill (`grad_school_planning.py`)

```python
class GradSchoolPlanningSkill(BaseSkill):
    code = "grad_school_planning"
    name = "考研规划"
    description = "考研院校选择、专业方向、备考时间线规划"
    icon = "🎓"
```

- **激活词**：考研、保研、研究生、读研、学硕、专硕、硕士
- **should_activate**：消息包含任一激活词
- **build_system_prompt**：注入用户上下文 + 知识库中"升学路径"分类文章，聚焦院校梯队选择、考试科目、分数线、备考策略
- **build_user_prompt**：包装用户消息，要求输出结构化方案
- **parse_response**：尝试从 LLM 回复中提取 JSON，字段：`target_schools`(list), `target_major`(str), `exam_subjects`(list), `timeline`(str), `prep_strategy`(str)，失败则返回原始内容

### 职业转型 Skill (`career_transition.py`)

```python
class CareerTransitionSkill(BaseSkill):
    code = "career_transition"
    name = "职业转型"
    description = "跨行业/跨岗位转型可行性分析与路径规划"
    icon = "🔄"
```

- **激活词**：转行、转型、跨行、换赛道、跨岗位
- **should_activate**：消息包含任一激活词
- **build_system_prompt**：注入用户上下文 + 知识库中"行业指南"和"岗位要求"分类文章，聚焦可迁移技能分析、差距评估、转型路径
- **build_user_prompt**：要求输出结构化方案
- **parse_response**：提取 JSON，字段：`current_field`(str), `target_field`(str), `transferable_skills`(list), `gaps`(list), `transition_steps`(list)

### 注册

两个 Skill 在 `registry.py` 的 `SKILL_REGISTRY` 中追加，自动被 `find_skill()` 按优先级匹配。优先级低于 `career_planning`（精确关键词匹配优先于模糊匹配）。

## B3：规划执行追踪

### 新模型 `MilestoneLog`

```python
class MilestoneLog(Base):
    __tablename__ = "milestone_logs"
    id = Column(String, primary_key=True, default=uuid4)
    plan_id = Column(String, ForeignKey("career_plans.id"), nullable=False)
    milestone_index = Column(Integer, nullable=False)  # 对应 milestones JSONB 数组的索引
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- 每个里程碑可有多条执行日志
- `milestone_index` 对应 `CareerPlan.milestones` JSONB 数组的索引位置
- 删除 CareerPlan 时级联删除关联日志

### 新 API 端点

在 `career_plans.py` 路由中追加：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/career-plans/{plan_id}/milestones/{idx}/logs` | 添加执行日志 |
| GET | `/api/career-plans/{plan_id}/milestones/{idx}/logs` | 列出里程碑日志 |
| DELETE | `/api/career-plans/{plan_id}/logs/{log_id}` | 删除日志 |
| GET | `/api/career-plans/reminders` | 到期提醒（按需计算） |

**到期提醒逻辑**（`GET /api/career-plans/reminders`）：
- 查询当前用户所有 `status == "active"` 的 CareerPlan
- 遍历每个 plan 的 milestones
- 分类：
  - `overdue`：`target_date < today` 且 `status != "done"`
  - `upcoming`：`target_date` 在未来 7 天内 且 `status != "done"`
- 返回：`[{plan_id, plan_goal, milestone_title, milestone_index, target_date, days_remaining, type: "overdue"|"upcoming"}]`
- 无需后台任务，请求时实时计算

### 新 Service 方法

在 `career_plan_service.py` 中追加：
- `add_milestone_log(db, user_id, plan_id, idx, content)` — 验证 plan 归属 + 索引有效
- `list_milestone_logs(db, user_id, plan_id, idx)` — 按时间倒序
- `delete_milestone_log(db, user_id, log_id)` — 验证归属
- `get_reminders(db, user_id)` — 计算到期提醒

### 新 Schema

```python
class MilestoneLogCreate(BaseModel):
    content: str

class MilestoneLogResponse(BaseModel):
    id: str
    plan_id: str
    milestone_index: int
    content: str
    created_at: datetime

class ReminderItem(BaseModel):
    plan_id: str
    plan_goal: str
    milestone_title: str
    milestone_index: int
    target_date: str | None
    days_remaining: int | None
    type: str  # "overdue" | "upcoming"
```

### 前端更新

**`/plans` 页面增强**：
- 里程碑展开时显示执行日志时间线（日期 + 内容）
- 每个里程碑下方添加日志输入框（Enter 提交）
- 日志可删除（hover 显示删除按钮）

**看板新增「规划提醒」卡片**：
- 展示逾期（红色）和即将到期（橙色）的里程碑
- 每条显示：计划目标 + 里程碑标题 + 剩余天数
- 点击跳转 `/plans`

**API 客户端补全**：
```typescript
careerPlansApi.addLog(planId, idx, content)
careerPlansApi.listLogs(planId, idx)
careerPlansApi.deleteLog(planId, logId)
careerPlansApi.getReminders()
```

## 文件清单

| 文件 | 操作 |
|------|------|
| `backend/app/skills/grad_school_planning.py` | 新建：考研规划 Skill |
| `backend/app/skills/career_transition.py` | 新建：职业转型 Skill |
| `backend/app/skills/registry.py` | 修改：注册 2 个新 Skill |
| `backend/app/models/milestone_log.py` | 新建：MilestoneLog 模型 |
| `backend/app/models/__init__.py` | 修改：注册 MilestoneLog |
| `backend/app/services/career_plan_service.py` | 修改：添加日志 CRUD + reminders |
| `backend/app/schemas/chat.py` | 修改：添加 MilestoneLog/ReminderItem schema |
| `backend/app/api/career_plans.py` | 修改：添加 4 个新端点 |
| `backend/tests/test_career_plans.py` | 修改：添加日志 + 提醒测试 |
| `backend/tests/test_skills.py` | 新建：Skills 激活/解析测试 |
| `frontend/app/(app)/plans/page.tsx` | 修改：里程碑日志时间线 + 输入框 |
| `frontend/app/(app)/dashboard/page.tsx` | 修改：添加规划提醒卡片 |
| `frontend/lib/api.ts` | 修改：补全 careerPlansApi 日志/提醒方法 |
| `frontend/types/index.ts` | 修改：添加 MilestoneLog/ReminderItem 类型 |

## 测试

- **后端**：新增 test_skills.py（Skill 激活/解析），test_career_plans.py 追加日志 CRUD + reminders 测试
- **前端**：tsc 编译通过 + next build 成功
- **手动验证**：新 Skill 在对话中正确激活、执行日志添加/删除、提醒卡片展示
