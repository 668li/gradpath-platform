# Phase 7 设计文档：外部数据接入 + AI 决策指导

> 日期：2026-07-01
> 状态：已批准

## 一、概述

GradPath 经过 6 个阶段的建设，已形成完整的数据闭环（用户提交 + 社区聚合 + 高校报告管道 + 讨论区），但缺少外部市场基准数据，且完全没有面向用户的 AI 决策指导功能。Phase 7 解决两个核心问题：

1. **数据充足**：接入国家统计局薪资数据、公司元数据、岗位薪资基准，让平台从"内循环"升级为"有外部参照系"
2. **AI 指导**：构建统一 AI 服务层，注入用户画像 + 外部数据 + 社区数据作为 context，LLM 生成个性化决策建议

## 二、新增数据模型

### 2.1 Company（公司元数据）

表名：`companies`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| name | String(200) unique | 公司名 |
| industry | String(50) | 行业（互联网/金融/制造/教育/医疗/咨询/能源/快消） |
| size | Enum(CompanySize) | startup(<50) / small(50-200) / medium(200-2000) / large(2000-10000) / giant(>10000) |
| stage | String(50) nullable | 融资阶段（未融资/天使轮/.../已上市） |
| headquarters | String(50) nullable | 总部城市 |
| description | Text nullable | 简介 |
| created_at / updated_at | DateTime | 时间戳 |

### 2.2 SalaryBenchmark（薪资基准）

表名：`salary_benchmarks`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| company | String(200) | 公司名（文本关联 Company.name） |
| position | String(200) | 岗位名 |
| city | String(50) nullable | 城市 |
| experience_level | Enum(ExperienceLevel) | entry / junior / mid / senior / lead |
| salary_min | Int | 最低月薪（元） |
| salary_median | Int | 中位数月薪 |
| salary_max | Int | 最高月薪 |
| source | String(50) | kaggle / stats_bureau / community |
| year | Int | 数据年份 |
| created_at / updated_at | DateTime | 时间戳 |

### 2.3 MarketData（市场宏观数据）

表名：`market_data`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| indicator | String(100) | 指标名 |
| category | String(50) | salary / employment_rate / industry_trend |
| value | Float | 数值 |
| unit | String(20) | 单位（元/%/万人） |
| region | String(50) nullable | 地区 |
| industry | String(50) nullable | 行业 |
| year | Int | 年份 |
| source | String(100) | 来源 |
| created_at / updated_at | DateTime | 时间戳 |

## 三、AI 决策指导服务

### 3.1 统一 AI 服务层

新增 `backend/app/services/ai_service.py`，封装所有 LLM 调用：

- 复用 `config.py` 的 `LLM_API_KEY` / `LLM_MODEL` / `LLM_BASE_URL`
- 调用方式与 `pipeline/extractor.py` 的 `call_llm` 一致（httpx POST，OpenAI 兼容接口）
- 支持 system_prompt + context injection
- `LLM_API_KEY` 为空时抛出 `AIServiceNotConfigured` 异常，API 层返回 503

### 3.2 决策指导 API

`POST /api/ai/decision-advice`

**请求体**：
```json
{
  "destination_type": "employment",
  "company": "腾讯",
  "position": "后端开发",
  "city": "深圳",
  "expected_salary": "25k_50k"
}
```

**Context 注入流程**（后端自动组装）：
1. 用户画像：技能树、职业事件（最近 5 条）、历史决策、学校专业
2. 外部基准：SalaryBenchmark（该公司该岗位薪资）、MarketData（行业趋势）、Company 元数据
3. 社区参考：CommunityReport 聚合（同类人去向）、InterviewReport 聚合（该公司面试经验）
4. Context 截断优先级：用户画像 > 薪资基准 > 社区数据 > 市场趋势

**LLM 输出**（JSON）：
```json
{
  "summary": "一句话总览",
  "pros": ["优势1", "优势2"],
  "cons": ["风险1", "风险2"],
  "market_analysis": "市场需求与薪资水平分析",
  "alternatives": [{"option": "备选方案", "reason": "推荐理由"}],
  "skill_gap": ["缺少技能1"],
  "confidence": 4,
  "advice": "个性化建议段落"
}
```

### 3.3 降级策略

- `LLM_API_KEY` 为空 → 返回 503 + 前端展示"AI 服务未配置"
- LLM 超时（30 秒）→ 返回 504 + 前端展示"AI 分析超时"
- LLM 返回非 JSON → 尝试提取 JSON 片段，失败则返回原始文本

## 四、种子数据

### 4.1 公司元数据（50+ 企业）

覆盖：互联网大厂（腾讯/阿里/字节/百度/美团/京东/网易/拼多多/快手/小红书）、金融（四大行/招商/中金/中信）、通信（华为/中兴）、外企（微软/谷歌/亚马逊/苹果）、国企（国家电网/中石油/中石化）、独角兽（大疆/理想/蔚来/小鹏）等。

### 4.2 薪资基准（200+ 条）

基于 Kaggle 真实数据集格式，按"公司×岗位×城市×经验级别"组合生成种子数据。覆盖 20+ 公司 × 10+ 岗位 × 3 城市 × 3 经验级别。

### 4.3 市场宏观数据（30+ 条）

国家统计局公开数据：2022-2024 年分行业年平均工资、城镇就业率、IT/金融/制造行业就业趋势。

## 五、前端

### 5.1 AI 决策分析组件

新增 `frontend/components/ai-advice.tsx`：
- 触发方式：在去向决策页新增"AI 分析"按钮
- 输入：用户选择意向（去向类型、公司、岗位、城市、期望薪资）
- 展示：结构化卡片（总览、利弊清单、市场分析、备选方案、技能差距、建议）
- 加载状态：骨架屏 + "AI 正在分析中…"
- 错误处理：503 展示"未配置"，504 展示"超时重试"

### 5.2 决策页集成

在 `/decisions` 页面的决策列表上方新增"AI 决策分析"入口，点击展开 AI 分析面板。

## 六、不做的事（YAGNI）

- 不爬 BOSS/拉勾/脉脉（反爬严、法律风险高）
- 不建公司评价系统（已有面试经验 + 讨论帖覆盖）
- 不做实时招聘数据同步
- 不做 AI 对话式聊天（本轮仅做单次分析，对话留后续阶段）
- 不引入 langchain 等 AI SDK（直接 httpx 调用，与 pipeline 一致）

## 七、测试策略

- 后端：模型 CRUD 测试 + AI service mock 测试（mock httpx 响应）+ API 集成测试
- 前端：tsc 类型检查 + build 验证 + E2E 浏览器验证
- AI 测试：mock LLM 返回，验证 context 组装逻辑和 JSON 解析
