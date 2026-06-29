# GradPath Phase 3 — 社区聚合设计文档

> **创建日期**：2026-06-29
> **阶段**：Phase 3 — 社区聚合参考（脱敏数据聚合 + "同类人去了哪"）
> **前置依赖**：Phase 2 已完成（就业报告数据管道 + 搜索 API + 探索页面）

---

## 1. 项目概述

### 1.1 一句话定义

Phase 3 为 GradPath 构建「社区去向聚合」功能，让用户匿名提交自己的毕业去向，系统聚合后展示"和你同校同专业的人实际去了哪里"，并与 Phase 2 的官方就业报告数据对比。

### 1.2 核心价值

Phase 2 提供宏观官方统计（就业率、雇主排名），Phase 3 补充微观真实样本：
- 官方数据是聚合后的比例，看不到个体故事
- 社区数据是真实用户的去向，更贴近"学长学姐实际去了哪"
- 两者对比可以发现"官方说就业率 45%，社区里实际去互联网的更多"

### 1.3 设计原则

1. **匿名优先**：提交需登录防刷，但展示层完全不暴露用户身份
2. **聚合阈值**：同校同专业样本数 ≥ 3 才展示分布，保护隐私
3. **与 Phase 2 互补**：探索结果页同时展示官方数据和社区数据
4. **渐进增长**：初期种子数据填充，后续靠用户自然提交增长

---

## 2. 数据模型

### 2.1 CommunityReport（匿名去向报告）

```python
class DestinationType(str, enum.Enum):
    employment = "employment"
    further_study = "further_study"
    civil_service = "civil_service"
    abroad = "abroad"
    startup = "startup"
    gap_year = "gap_year"

class SalaryRange(str, enum.Enum):
    below_8k = "below_8k"
    r8k_15k = "8k_15k"
    r15k_25k = "15k_25k"
    r25k_50k = "25k_50k"
    above_50k = "above_50k"
    prefer_not = "prefer_not"

class CommunityReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "community_reports"

    # 背景信息
    school_name: Mapped[str] = mapped_column(String(100), nullable=False)
    major: Mapped[str] = mapped_column(String(200), nullable=False)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False)
    degree: Mapped[Degree] = mapped_column(Enum(Degree), default=Degree.bachelor, nullable=False)

    # 去向信息
    destination_type: Mapped[DestinationType] = mapped_column(Enum(DestinationType), nullable=False)
    employer: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(50))
    salary_range: Mapped[SalaryRange | None] = mapped_column(Enum(SalaryRange))

    # 匿名标识：不存 user_id 在展示层，仅用于防重复提交检查
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
```

### 2.2 唯一约束

- `(user_id, graduation_year)` 唯一：同一用户同年只能提交一次（可修改，不能重复提交）

### 2.3 与现有模型关系

- `Degree` 枚举复用 Phase 2 的 `app/models/employment_data.py`
- 不与 `School` 表做外键关联（用户可能输入系统未收录的学校）
- `user_id` 关联 `users.id`，但不在前端展示

---

## 3. API 设计

### 3.1 提交去向报告

```
POST /api/community/submit
Authorization: Bearer <token>
```

请求体：
```json
{
  "school_name": "清华大学",
  "major": "机械工程",
  "graduation_year": 2024,
  "degree": "bachelor",
  "destination_type": "employment",
  "employer": "三一重工",
  "city": "北京",
  "industry": "制造业",
  "salary_range": "15k_25k"
}
```

逻辑：
- 若该 user_id + graduation_year 已存在，更新而非新建
- 返回提交成功 + 当前聚合统计快照

### 3.2 查询聚合

```
POST /api/community/aggregate
```

请求体：
```json
{
  "school": "清华大学",
  "major": "机械工程",
  "year": 2024
}
```

返回结构：
```json
{
  "school": "清华大学",
  "major": "机械工程",
  "sample_count": 12,
  "sufficient": true,
  "destination_distribution": {
    "employment": 0.50,
    "further_study": 0.33,
    "civil_service": 0.08,
    "abroad": 0.09
  },
  "top_employers": [
    {"name": "三一重工", "count": 3},
    {"name": "比亚迪", "count": 2}
  ],
  "top_cities": [
    {"name": "北京", "count": 5},
    {"name": "上海", "count": 2}
  ],
  "top_industries": [
    {"name": "制造业", "count": 4},
    {"name": "互联网", "count": 2}
  ],
  "salary_distribution": {
    "below_8k": 1,
    "8k_15k": 2,
    "15k_25k": 3,
    "25k_50k": 1
  }
}
```

当 `sample_count < 3` 时，`sufficient = false`，仅返回 `sample_count` 不返回分布。

### 3.3 对比官方数据

```
POST /api/community/compare
```

请求体同 3.2，返回官方报告数据 + 社区数据并排对比。

### 3.4 社区统计

```
GET /api/community/stats
```

返回：总样本数、覆盖学校数、覆盖专业数、最新提交时间。

---

## 4. 前端设计

### 4.1 新增页面

```
app/(app)/community/
├── page.tsx          # 提交表单 + 我的提交记录
└── result/page.tsx   # 聚合结果展示（与官方对比）
```

### 4.2 提交表单 `/community`

- 学校输入（带自动补全，复用 Phase 2 的 schools API）
- 专业输入（带自动补全，复用 majors API）
- 毕业年份（下拉：2019-2025）
- 学历（下拉：本科/硕士/博士）
- 去向类型（单选按钮：就业/升学/考公/出国/创业/间隔年）
- 根据去向类型动态显示：
  - 就业：雇主、城市、行业、薪资范围
  - 升学：学校名称
  - 其他：城市
- 提交后显示"已提交"状态 + 当前聚合快照

### 4.3 聚合结果 `/community/result`

- 去向分布饼图（社区数据）
- 热门雇主排名（横向条形图）
- 城市分布（横向条形图）
- 薪资分布（柱状图）
- 与官方数据对比卡片（左右并排）

### 4.4 导航更新

```
个人看板 | 去向探索 | 社区数据 | 去向决策 | 成长时间线 | 技能树 | 阶段复盘
```

### 4.5 探索结果页衔接

`/explore/result` 底部新增"社区数据"卡片：
- 若有社区数据：展示去向分布对比（官方 vs 社区）
- 若无数据：CTA "分享你的去向，帮助学弟学妹" → 跳转 `/community`

---

## 5. 种子数据

为 10 所学校每校生成 3-5 条社区报告（模拟不同用户提交），共约 40 条种子数据。

| 学校 | 样本数 | 专业覆盖 |
|------|--------|---------|
| 清华大学 | 5 | 机械工程(2), 计算机(2), 电子工程(1) |
| 北京大学 | 4 | 计算机(2), 金融学(1), 法学(1) |
| 浙江大学 | 4 | 计算机(2), 机械工程(1), 化学(1) |
| 上海交大 | 3 | 机械工程(1), 计算机(1), 电子信息(1) |
| 复旦大学 | 3 | 金融学(1), 新闻学(1), 数学(1) |
| ... | ... | ... |

---

## 6. 隐私与安全

1. **匿名展示**：API 返回不含 user_id、name、email 等身份信息
2. **聚合阈值**：sample_count < 3 时不展示分布
3. **防重复提交**：user_id + graduation_year 唯一约束
4. **数据审核**：后续可增加内容审核（employer 等文本字段的敏感词过滤）
5. **删除权**：用户可删除自己的提交

---

## 7. 验收标准

1. 用户能提交匿名去向报告并查看自己的提交
2. 聚合 API 返回正确的去向分布、热门雇主、城市分布
3. sample_count < 3 时不展示分布
4. 探索结果页展示社区数据对比卡片
5. 导航栏新增"社区数据"入口
6. 种子数据 40+ 条已入库
7. 所有后端测试通过，前端构建通过
