# GradPath Phase 11: AI 职业规划管家

## 概述

将 GradPath 从数据追踪工具升级为 AI 职业规划管家。核心差异化：基于用户真实数据 + 就业市场数据 + 职业知识库，通过可叠加的 Skill 系统提供有记忆、可执行的职业规划指导。

## 四大模块

### 1. 知识库
- `KnowledgeArticle` 模型：category/title/content(Markdown)/tags/source/metadata
- 6 大分类：行业指南、岗位要求、技能图谱、面试攻略、薪资参考、升学路径
- ~50 篇种子数据
- API: 分页列表 + 搜索 + 详情 + 管理员 CRUD

### 2. Skill 系统
- `BaseSkill` 统一接口：should_activate / build_system_prompt / build_user_prompt / parse_response
- 3 个内置 Skill：career_path_planning / resume_diagnosis / interview_simulation
- 自动识别意图激活，或用户显式 @skill 指定
- 默认通用咨询 Skill 兜底

### 3. 管家对话
- `Conversation` + `Message` 模型，对话历史持久化
- 每次对话注入完整用户上下文（技能/事件/决策/复盘/成长洞察）
- 记录 skill_used 和 context_snapshot
- 对话 API: CRUD + 发送消息

### 4. 职业规划方案
- `CareerPlan` 模型：goal/current_state/target_state/gaps/milestones/timeline
- 由 career_path_planning Skill 生成
- 里程碑可追踪状态（draft/active/completed）
- 规划 API: 列表 + 详情 + 里程碑更新

## 前端
- `/chat` 页面：对话界面（左侧列表 + 右侧聊天）
- `/plans` 页面：规划列表与里程碑追踪
- Skill 选择器 + Markdown 渲染 + 规划卡片
