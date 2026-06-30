# GradPath Phase 4 — 公司面试经验聚合设计文档

> **创建日期**：2026-06-30
> **阶段**：Phase 4 — 公司面试经验聚合（"这家公司面试官看重什么"）
> **前置依赖**：Phase 3 社区聚合已完成（CommunityReport 模型 + 提交/聚合 API + 社区页面）

---

## 1. 项目概述

### 1.1 一句话定义

Phase 4 为 GradPath 构建「公司面试经验聚合」功能，让用户匿名分享面试经历，系统按公司+岗位聚合后展示"这家公司面试官实际看重什么能力"，帮助同背景（同学历/同专业）的人做面试准备。

### 1.2 核心价值

Phase 2 回答"同专业的人去了哪些公司"，Phase 3 回答"真实学长学姐去了哪"，Phase 4 回答"去了那家公司后，面试官到底看重什么"：

- 官方就业报告只有雇主排名，没有面试信息
- 社区去向数据只有"去了哪"，没有"怎么去的"
- Phase 4 补充最后一环：面试考察维度、难度、轮数、结果分布

### 1.3 设计原则

1. **结构化优先**：面试信息通过预定义标签结构化采集，保证聚合数据质量
2. **复用 Phase 3 模式**：匿名提交 + 登录防刷 + 聚合阈值（≥3 才展示详细分布）
3. **可选关联**：面试报告可独立提交，也可关联到社区去向报告
4. **YAGNI**：Phase 4 不引入 LLM，纯靠结构化表单 + 标签统计；LLM 提炼留给后续迭代

---

## 2. 数据模型

### 2.1 新增枚举

```python
class InterviewDimension(str, enum.Enum):
    algorithm = "algorithm"           # 算法/编程
    system_design = "system_design"   # 系统设计
    project_depth = "project_depth"   # 项目深度
    culture_fit = "culture_fit"       # 文化匹配
    communication = "communication"   # 沟通表达
    domain_knowledge = "domain"       # 专业知识
    behavior = "behavior"             # 行为面试

class InterviewResult(str, enum.Enum):
    offer = "offer"
    rejected = "rejected"
    pending = "pending"
```

### 2.2 InterviewReport 模型

```python
class InterviewReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "interview_reports"

    # 关联社区报告（可选：面试报告可独立提交，也可关联去向报告）
    community_report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("community_reports.id"), nullable=True
    )

    # 公司信息
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    # 面试信息
    interview_year: Mapped[int] = mapped_column(Integer, nullable=False)
    rounds: Mapped[int | None] = mapped_column(Integer)  # 面试轮数
    result: Mapped[InterviewResult] = mapped_column(
        Enum(InterviewResult), default=InterviewResult.pending, nullable=False
    )

    # 结构化考察维度（多选，JSON 数组）
    dimensions: Mapped[list] = mapped_column(JSONB, default=list)
    # ["algorithm", "system_design", "project_depth"]

    difficulty: Mapped[int | None] = mapped_column(Integer)  # 1-5 分

    # 可选文本（一句话总结，非必填）
    summary: Mapped[str | None] = mapped_column(Text)

    # 用户关联
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
```

### 2.3 唯一约束

- `(user_id, company, position, interview_year)` 唯一：同一用户同年同公司同岗位只保留一条（upsert 语义）

### 2.4 与现有模型的关系

- `InterviewReport.community_report_id` 可选关联到 `CommunityReport`，实现"提交去向时顺带分享面试经历"
- `InterviewReport.user_id` 关联到 `User`，与 `CommunityReport` 保持一致的权限模型
- 新模型注册到 `app/models/__init__.py`，`Base.metadata.create_all()` 自动建表

---

## 3. API 设计

### 3.1 端点总览

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/interview/submit` | POST | 需登录 | 提交面试报告（upsert） |
| `/api/interview/my-reports` | GET | 需登录 | 我的面试记录列表 |
| `/api/interview/{report_id}` | DELETE | 需登录 | 删除我的面试记录 |
| `/api/interview/aggregate` | POST | 无需登录 | 按公司+岗位聚合面试数据 |
| `/api/interview/stats` | GET | 无需登录 | 全局统计（总样本/公司数/岗位数） |
| `/api/interview/companies` | POST | 无需登录 | 已收录公司列表（含样本数，支持模糊搜索） |

### 3.2 聚合 API 详细设计

**请求**：`POST /api/interview/aggregate`

```json
{
  "company": "腾讯",
  "position": "后端开发"
}
```

- `company`：必填，ILIKE 模糊匹配
- `position`：可选，不传则聚合该公司的所有岗位

**响应**：

```json
{
  "company": "腾讯",
  "position": "后端开发",
  "sample_count": 5,
  "sufficient": true,
  "avg_difficulty": 3.6,
  "avg_rounds": 3.2,
  "result_distribution": {
    "offer": 0.4,
    "rejected": 0.4,
    "pending": 0.2
  },
  "dimension_frequency": {
    "algorithm": 0.8,
    "system_design": 0.6,
    "project_depth": 0.4,
    "culture_fit": 0.2,
    "communication": 0.3,
    "domain": 0.2,
    "behavior": 0.1
  },
  "common_positions": ["后端开发", "前端开发", "算法工程师"]
}
```

### 3.3 聚合逻辑

1. `company ILIKE '%公司名%'` 模糊匹配
2. 若传入 `position`，额外 `position ILIKE '%岗位名%'`
3. `sample_count < 3` 时 `sufficient = false`，不返回 `dimension_frequency` 和 `result_distribution`
4. `dimension_frequency`：统计每个维度出现的次数 / 总样本数（0-1 比例）
5. `result_distribution`：各结果类型计数 / 总样本数（0-1 比例）
6. `avg_difficulty` / `avg_rounds`：仅计算非空值的平均值

---

## 4. 前端设计

### 4.1 新增页面

```
app/(app)/interview/
  ├── page.tsx              # 面试分享提交页
  └── result/
      └── page.tsx          # 公司面试聚合结果页
```

### 4.2 提交页（`/interview`）

**布局**：

1. **顶部统计卡片**：总样本数 / 覆盖公司数 / 覆盖岗位数
2. **提交表单**（card）：
   - 公司（必填，带 autocomplete，从已收录学校+预置列表拉取）
   - 岗位（必填，纯文本输入）
   - 城市（可选）
   - 面试年份（必填，下拉 2019-2025）
   - 面试轮数（可选，数字输入 1-10）
   - 面试结果（必填，按钮组：拿到 offer / 未通过 / 进行中）
   - 考察维度（必填，多选按钮组：算法/系统设计/项目深度/文化匹配/沟通表达/专业知识/行为面试）
   - 难度评分（可选，1-5 星）
   - 一句话总结（可选，textarea，限 200 字）
3. **操作按钮**：提交报告 / 查看聚合结果
4. **我的提交记录**（card）：列表展示已提交的面试报告，支持删除和"查看聚合"

### 4.3 聚合结果页（`/interview/result`）

**URL 参数**：`?c={base64_company}&p={base64_position}`

**展示内容**：

1. **标题**：公司名 · 岗位名
2. **样本提示**：已聚合 N 份匿名报告 / 样本不足提示
3. **考察维度雷达图**（RadarChart）：7 个维度的频率，直观展示"这家公司最看重什么"
4. **面试难度分布**（柱状图）：1-5 分各有多少人
5. **面试结果分布**（饼图）：offer / rejected / pending
6. **基本信息**：平均轮数、平均难度
7. **常见岗位**（若未指定岗位）：该公司其他常见岗位列表
8. **CTA**：提交我的面试经历

### 4.4 探索结果页增强

在 `explore/result` 页面的社区数据卡片下方，新增"面试经验"区块：

- 当用户搜索"清华大学 计算机科学与技术"时，展示该专业热门雇主的面试聚合摘要
- 从社区去向数据中提取热门雇主，调用面试聚合 API 展示该公司的考察维度 Top3
- 点击"查看完整面试画像"跳转到 `/interview/result`

### 4.5 导航更新

在 `nav.tsx` 的导航项中，在"社区数据"之后添加：

```tsx
{ href: "/interview", label: "面试经验", icon: Briefcase }
```

---

## 5. 种子数据

### 5.1 种子用户

复用 Phase 3 的 `community_seed_1@test.com` ~ `community_seed_10@test.com`。

### 5.2 种子面试报告

10 家公司，每家 3-5 条，共约 40 条：

| 公司 | 行业 | 岗位 | 考察维度侧重 |
|------|------|------|-------------|
| 腾讯 | 互联网 | 后端开发/前端开发/算法 | 算法+系统设计 |
| 字节跳动 | 互联网 | 后端开发/客户端开发 | 算法+项目深度 |
| 阿里巴巴 | 互联网 | 后端开发/数据分析 | 系统设计+项目深度 |
| 华为 | 通讯 | 硬件工程师/算法 | 专业知识+项目深度 |
| 百度 | 互联网 | 算法工程师/后端 | 算法+系统设计 |
| 中金公司 | 金融 | 投行分析师/研究员 | 专业知识+沟通表达 |
| 中信证券 | 金融 | 研究员/投行 | 专业知识+行为面试 |
| 三一重工 | 制造业 | 机械工程师/项目经理 | 专业知识+项目深度 |
| 比亚迪 | 制造业 | 电池工程师/嵌入式 | 专业知识+文化匹配 |
| 大疆 | 硬件 | 算法工程师/嵌入式 | 算法+项目深度 |

每条种子数据包含：公司、岗位、城市、年份、轮数、结果、维度（2-4 个）、难度（1-5）、一句话总结。

### 5.3 幂等性

种子脚本在插入前删除 `user_id IN (seed_users)` 的所有面试报告，保证可重复执行。

---

## 6. 目录结构

### 6.1 后端

```
backend/
  ├── app/
  │   ├── models/
  │   │   └── interview_report.py      # InterviewReport + 枚举
  │   ├── schemas/
  │   │   └── interview.py             # Pydantic schemas
  │   ├── services/
  │   │   └── interview_service.py     # 提交/聚合/统计逻辑
  │   └── api/
  │       └── interview.py             # 6 个端点
  ├── pipeline/
  │   └── seed_interview.py            # 种子数据脚本
  └── tests/
      └── test_api_interview.py        # 测试用例
```

### 6.2 前端

```
frontend/
  ├── app/(app)/interview/
  │   ├── page.tsx                      # 提交页
  │   └── result/page.tsx              # 聚合结果页
  ├── components/
  │   └── interview-charts.tsx         # 雷达图+难度分布+结果饼图
  ├── types/
  │   └── index.ts                     # 新增 InterviewReport 等类型
  └── lib/
      ├── api.ts                        # 新增 interviewApi
      └── constants.ts                  # 新增维度/结果标签映射
```

---

## 7. 隐私与安全

### 7.1 匿名展示

- 聚合结果完全不暴露用户身份
- 提交记录仅用户本人可见（`my-reports` 接口按 `user_id` 过滤）

### 7.2 聚合阈值

- `sample_count >= 3` 才展示 `dimension_frequency` 和 `result_distribution`
- 不足 3 时仅返回 `sample_count` 和 `sufficient: false`

### 7.3 输入校验

- `company` 和 `position` 长度 1-200 字符
- `difficulty` 范围 1-5
- `rounds` 范围 1-10
- `dimensions` 必须是有效的 `InterviewDimension` 枚举值
- `summary` 长度限制 200 字符

---

## 8. 测试计划

### 8.1 后端测试（test_api_interview.py）

- 提交面试报告（正常流程）
- Upsert 语义（同用户同公司同岗位同年覆盖）
- 未登录提交返回 401
- 获取我的报告列表
- 删除自己的报告
- 删除他人报告返回 403
- 聚合：样本充足时返回完整分布
- 聚合：样本不足时返回 sufficient=false
- 聚合：模糊匹配公司名
- 聚合：按岗位过滤
- 全局统计
- 公司列表搜索
- 输入校验（难度超范围、维度无效值）

### 8.2 前端验证

- `next build` 通过
- 提交表单所有字段正常工作
- 聚合结果页雷达图/柱状图/饼图正确渲染
- 探索结果页面试经验区块展示
- 导航新增"面试经验"入口

---

## 9. 不在 Phase 4 范围内

以下功能明确排除，留给后续迭代：

- **LLM 自由文本提炼**：Phase 4 仅用结构化标签，不引入 LLM
- **面试题目级分享**：Phase 4 只记录考察维度，不记录具体题目
- **面试时间线**：不记录每轮面试的详细信息，只记录总轮数
- **公司官方招聘标准接入**：不抓取公司官方 JD，仅靠用户分享
- **匹配推荐**：不基于用户 profile 推荐面试准备方向
