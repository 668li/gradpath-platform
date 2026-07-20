# AI对话增强设计文档

## [S1] 问题

GradPath的AI对话系统已有基础Skill框架（12个Skill），但存在以下不足：
1. 单轮对话为主，缺乏多轮交互能力
2. Skill匹配仅基于关键词，缺乏上下文感知
3. 缺少薪资谈判和行业分析等高价值Skill

## [S2] 解决方案概览

### 2.1 多轮对话能力增强
- **InterviewSimulationSkill**：支持多轮面试模拟，面试官提问→用户回答→评分反馈
- **CareerPlanningSkill**：支持逐步细化职业规划，根据用户反馈调整建议

### 2.2 上下文感知改进
- 改进 `find_skill_instance`，支持基于对话历史的智能匹配
- 新增对话状态管理（当前话题、用户情绪）

### 2.3 新增Skill
- **SalaryNegotiationSkill**：薪资谈判助手，帮助用户准备谈薪策略
- **IndustryAnalyzerSkill**：行业分析器，分析目标行业的趋势和机会

## [S3] 架构设计

### 3.1 多轮对话架构
```
用户消息 → Skill匹配 → 上下文构建 → LLM调用 → 响应解析 → 状态更新
    ↑                                                              ↓
    └────────────────── 对话历史 ──────────────────────────────────┘
```

### 3.2 Skill扩展
- 新增 `SalaryNegotiationSkill`：code="salary_negotiation"
- 新增 `IndustryAnalyzerSkill`：code="industry_analyzer"
- 在 `_SKILLS` 注册表中注册

### 3.3 上下文管理
- 在 `chat_service.py` 中新增 `ConversationContext` 类
- 管理对话状态（当前话题、用户情绪、历史摘要）

## [S4] 数据流

1. 用户发送消息
2. `find_skill_instance` 匹配Skill（支持上下文感知）
3. Skill构建prompt（含对话历史）
4. LLM生成响应
5. Skill解析响应
6. 更新对话状态

## [S5] 错误处理

- LLM超时：返回友好提示，建议稍后重试
- Skill匹配失败：使用default Skill兜底
- 响应解析失败：返回原始LLM响应

## [S6] 测试策略

- 单元测试：每个Skill的 `should_activate`、`build_system_prompt`、`parse_response`
- 集成测试：多轮对话流程
- 端到端测试：完整用户场景
