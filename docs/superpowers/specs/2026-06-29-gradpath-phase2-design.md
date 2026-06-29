# GradPath Phase 2 — 高校就业质量报告数据管道设计文档

> **项目代号**：GradPath / 职径
> **创建日期**：2026-06-29
> **阶段**：Phase 2 — 公开报告数据管道
> **前置依赖**：Phase 1 MVP 已完成（个人轨迹核心功能 + ReferenceSnapshot 模型预留）

---

## 1. 项目概述

### 1.1 一句话定义

Phase 2 为 GradPath 构建「高校就业质量报告数据管道」，抓取各高校公开发布的就业质量年度报告，通过 LLM 解析为结构化数据，使用户能搜索"清华大学 机械工程"并查看往年同专业学生的毕业去向分布、重点单位排名和多年趋势。

### 1.2 背景与动机

Phase 1 完成了个人轨迹记录功能，但用户的核心诉求是"参考同专业学长学姐去了哪里"。调研发现：

- 教育部自 2013 年要求各高校公开发布《毕业生就业质量年度报告》，数据公开且结构标准化（六篇式：规模结构、去向分析、代表性专业、质量分析、趋势预测、优化建议）
- 报告散布在各高校就业网/信息公开网，格式不统一（HTML 表格/PDF 混排）
- **无现成开源抓取项目或结构化开放数据集**
- 采集公开聚合统计数据的合规风险较低，但须避免触碰个人微观数据

### 1.3 核心设计原则

1. **LLM 辅助通用管道**：一套管道处理所有高校，新学校无需写新代码
2. **四步流水线**：fetch → extract → review → publish，人工把关数据质量
3. **结构化存储**：报告数据按学校/专业/年份/学位维度拆分存储，支持高效查询
4. **合规优先**：仅采集公开聚合统计数据，遵守 robots.txt，不触碰个人信息
5. **渐进扩展**：先验证 3 所标杆高校，跑通后批量扩展

---

## 2. 数据模型

### 2.1 新增模型

在现有 `ReferenceSnapshot`（保留给 Phase 3 社区聚合）之外，新增三张表：

#### School（学校）

```python
class School(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # URL友好标识符，如 tsinghua
    code: Mapped[str | None] = mapped_column(String(10))  # 教育部学校代码
    report_index_url: Mapped[str | None] = mapped_column(Text)  # 就业报告入口页URL
    province: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(20))  # 985/211/双一流/普通
```

#### ReportRecord（报告记录）

```python
class ParseStatus(str, enum.Enum):
    pending = "pending"
    parsed = "parsed"
    failed = "failed"
    reviewed = "reviewed"
    published = "published"

class ReportRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "report_records"

    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)  # 报告年份
    source_url: Mapped[str] = mapped_column(Text, nullable=False)  # 报告原始URL
    raw_html: Mapped[str | None] = mapped_column(Text)  # 原始HTML存档
    raw_pdf_path: Mapped[str | None] = mapped_column(String(500))  # PDF文件路径（如有）
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus), default=ParseStatus.pending, nullable=False
    )
    parse_error: Mapped[str | None] = mapped_column(Text)  # 解析失败原因
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    school: Mapped["School"] = relationship(back_populates="reports")
    employment_data: Mapped[list["EmploymentData"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
```

#### EmploymentData（结构化就业数据，按专业维度）

```python
class Degree(str, enum.Enum):
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    all = "all"  # 不区分学历的报告

class EmploymentData(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employment_data"

    report_id: Mapped[UUID] = mapped_column(ForeignKey("report_records.id"), nullable=False)
    major: Mapped[str] = mapped_column(String(200), nullable=False)  # 专业名称
    degree: Mapped[Degree] = mapped_column(Enum(Degree), default=Degree.all, nullable=False)
    total_graduates: Mapped[int | None] = mapped_column(Integer)  # 毕业总人数

    # 去向分布比例（0-1 之间的小数）
    employment_rate: Mapped[float | None] = mapped_column(Float)
    further_study_rate: Mapped[float | None] = mapped_column(Float)
    civil_service_rate: Mapped[float | None] = mapped_column(Float)
    abroad_rate: Mapped[float | None] = mapped_column(Float)
    startup_rate: Mapped[float | None] = mapped_column(Float)
    gap_year_rate: Mapped[float | None] = mapped_column(Float)

    # JSONB 结构化排名数据
    employer_ranking: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "三一重工", "count": 15}, {"name": "比亚迪", "count": 12}]

    industry_distribution: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"制造业": 0.4, "互联网": 0.2, "金融": 0.1}

    destination_region: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"北京": 0.3, "上海": 0.15, "广东": 0.1}

    school_for_further_study: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "清华大学", "count": 20}, {"name": "北京大学", "count": 5}]

    report: Mapped["ReportRecord"] = relationship(back_populates="employment_data")
```

### 2.2 唯一约束

- `School.name` 唯一，`School.slug` 唯一
- `(school_id, year)` 在 `ReportRecord` 上唯一（同一学校同年只有一份报告）
- `(report_id, major, degree)` 在 `EmploymentData` 上唯一

### 2.3 与现有代码的关系

- `ReferenceSnapshot` 模型保持不动，Phase 3 社区聚合时复用
- `DestinationDecision.reference_snapshot_id` 后续可关联到 `EmploymentData`，在决策时展示"同专业往年去向"参考
- 新增模型注册到 `app/models/__init__.py`，`Base.metadata.create_all()` 自动建表

---

## 3. 数据采集管道

### 3.1 管道架构

```
[1] fetch  →  [2] extract  →  [3] review  →  [4] publish
 下载HTML/PDF    LLM解析结构化    人工抽检修正     标记为已发布
```

### 3.2 目录结构

```
backend/pipeline/
  ├── __init__.py
  ├── cli.py              # Click CLI 入口
  ├── fetcher.py           # 网页/PDF抓取
  ├── extractor.py         # LLM 解析 + prompt 管理
  ├── reviewer.py          # 终端抽检输出
  └── prompts/
      └── extract_report.txt  # LLM 提示词模板
```

### 3.3 fetch（抓取）

**命令**：`python -m pipeline fetch --school tsinghua --year 2024`

**流程**：
1. 从 `School.report_index_url` 获取入口页
2. 解析入口页，定位指定年份的报告链接
3. 下载 HTML 内容（PDF 则存到 `backend/data/pdfs/` 目录）
4. 存入 `ReportRecord.raw_html`，`parse_status = "pending"`
5. 遵守 robots.txt，请求间隔 3-5 秒，设置 User-Agent

**边界处理**：
- 报告链接未找到 → 记录 `parse_error`，状态为 `failed`
- 页面需登录 → 跳过并提示需手动提供 URL
- 网络超时 → 重试 3 次，间隔递增

### 3.4 extract（LLM 解析）

**命令**：`python -m pipeline extract --report-id <uuid>`

**流程**：
1. 读取 `ReportRecord.raw_html`，用 BeautifulSoup 清洗为纯文本 + 表格片段
2. PDF 用 pdfplumber 提取文本
3. 文本过长时按章节分块，逐块解析
4. 调用 LLM API，prompt 要求返回严格 JSON：
   ```json
   {
     "majors": [
       {
         "major": "机械工程",
         "degree": "bachelor",
         "total_graduates": 120,
         "employment_rate": 0.45,
         "further_study_rate": 0.35,
         "civil_service_rate": 0.10,
         "abroad_rate": 0.10,
         "employer_ranking": [{"name": "三一重工", "count": 15}],
         "industry_distribution": {"制造业": 0.4},
         "destination_region": {"北京": 0.3},
         "school_for_further_study": [{"name": "清华大学", "count": 20}]
       }
     ]
   }
   ```
5. 按 `majors` 数组写入多条 `EmploymentData` 记录
6. `parse_status = "parsed"`，记录 `parsed_at`
7. LLM 返回非法 JSON 或解析异常 → `parse_status = "failed"`，记录错误

**LLM 配置**：
- 模型：智谱 GLM-4 或 OpenAI GPT-4o（通过 `.env` 配置）
- Temperature：0（确保稳定输出）
- 超时：60 秒

### 3.5 review（人工抽检）

**命令**：`python -m pipeline review --report-id <uuid>`

**流程**：
1. 终端输出解析结果摘要：每个专业的去向比例 + top5 雇主 + top5 升学去向
2. 管理员对比原始报告确认准确性
3. 输入 `y` 确认 → `parse_status = "reviewed"`
4. 输入 `n` 拒绝 → 回退为 `pending`，可调整 prompt 后重新 extract

### 3.6 publish（发布）

**命令**：`python -m pipeline publish --report-id <uuid>`

- 仅 `parse_status = "reviewed"` 的记录可发布
- 发布后 `parse_status = "published"`，数据对前端搜索可见

---

## 4. 搜索 API

### 4.1 核心搜索接口

```
GET /api/employment/search?school=清华大学&major=机械&year=2024
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| school | string | 是 | 学校名称（模糊匹配） |
| major | string | 是 | 专业名称（模糊匹配） |
| year | int | 否 | 不传则返回所有年份 |
| degree | string | 否 | bachelor/master/phd/all |

**返回结构**：
```json
{
  "school": {"name": "清华大学", "code": "10003"},
  "major": "机械工程",
  "records": [
    {
      "year": 2024,
      "degree": "bachelor",
      "total_graduates": 120,
      "rates": {
        "employment": 0.45,
        "further_study": 0.35,
        "civil_service": 0.10,
        "abroad": 0.10
      },
      "employer_ranking": [{"name": "三一重工", "count": 15}],
      "industry_distribution": {"制造业": 0.4},
      "destination_region": {"北京": 0.3},
      "school_for_further_study": [{"name": "清华大学", "count": 20}]
    }
  ],
  "trend": {
    "years": [2022, 2023, 2024],
    "employment_rate": [0.50, 0.48, 0.45],
    "further_study_rate": [0.30, 0.33, 0.35]
  }
}
```

**查询逻辑**：
- `School.name ILIKE '%学校%'` 模糊匹配
- `EmploymentData.major ILIKE '%专业%'` 模糊匹配
- 仅返回 `parse_status = "published"` 的报告关联数据
- `records` 按年份降序排列
- `trend` 自动聚合多年数据，按年份升序排列各比例字段

### 4.2 辅助接口

| 接口 | 说明 |
|------|------|
| `GET /api/employment/schools` | 学校列表（含已收录报告数、专业数） |
| `GET /api/employment/majors?school=清华大学` | 某校已收录专业列表 |
| `GET /api/employment/stats` | 全局统计（已收录学校数、报告数、专业数、年份范围） |

### 4.3 API 目录结构

```
backend/app/
  ├── schemas/
  │   └── employment.py        # EmploymentSearchResponse, SchoolResponse 等
  ├── api/
  │   └── employment.py        # 4 个端点
  └── services/
      └── employment_service.py  # 搜索/聚合逻辑
```

---

## 5. 前端搜索体验

### 5.1 新增页面

```
app/(app)/explore/
  ├── page.tsx                 # 搜索首页（搜索栏 + 已收录学校列表）
  └── result/page.tsx          # 搜索结果页（三块卡片）
```

### 5.2 搜索首页 `/explore`

- 顶部大搜索栏：学校输入框（带自动补全）+ 专业输入框（带自动补全）+ 年份下拉
- 下方展示已收录学校列表（卡片式），显示每校已收录专业数和年份范围
- 无搜索时展示全局统计：「已收录 X 所高校、Y 份报告、Z 个专业」

### 5.3 搜索结果页 `/explore/result`

三块卡片纵向排列：

**卡片一：去向分布饼图**
- 就业/升学/考公/出国/创业/间隔年的比例饼图
- 中心显示总毕业人数
- 用 Recharts PieChart，复用现有 PIE_COLORS

**卡片二：重点单位/升学去向排名**
- Tab 切换：「就业单位」/「升学去向」
- 横向条形图，top 10，显示名称 + 人数
- 用 Recharts BarChart

**卡片三：多年趋势折线图**
- X 轴：年份
- Y 轴：百分比
- 4 条线：就业率、升学率、考公率、出国率
- 用 Recharts LineChart

### 5.4 空结果处理

- 提示"该学校/专业暂无数据"
- 展示已收录学校列表，引导用户选择已有数据
- CTA："你的学校不在列表中？后续将支持更多高校"

### 5.5 与现有功能衔接

- 搜索结果页底部 CTA："记录你的去向决策"，跳转 `/decisions`，URL 带上 `?school=清华&major=机械` 预填参数
- Dashboard 新增"同专业参考"侧边卡片，展示当前用户学校+专业的去向概览（有数据时才显示）

### 5.6 导航更新

导航栏新增「去向探索」入口，排序在「个人看板」之后：

```
个人看板 | 去向探索 | 去向决策 | 成长时间线 | 技能树 | 阶段复盘
```

### 5.7 前端类型与 API 客户端

```
frontend/
  ├── types/index.ts           # 新增 EmploymentSearchResult, SchoolInfo 等类型
  └── lib/api.ts               # 新增 employmentApi 对象（search/schools/majors/stats）
```

---

## 6. 种子数据与测试策略

### 6.1 种子数据

| 学校 | 专业 | 年份 | 报告来源 |
|------|------|------|---------|
| 清华大学 | 机械工程、计算机科学与技术、电子工程 | 2023, 2024 | career.tsinghua.edu.cn |
| 北京大学 | 计算机科学与技术、金融学、法学 | 2023, 2024 | scc.pku.edu.cn |
| 浙江大学 | 计算机科学与技术、机械工程、化学 | 2023, 2024 | www.career.zju.edu.cn |

预计产出 3 校 × 3 专业 × 2 年 = 18 条 EmploymentData 记录。

### 6.2 后端测试

| 测试文件 | 覆盖内容 |
|----------|---------|
| `test_models_employment.py` | School / ReportRecord / EmploymentData 模型 CRUD + 唯一约束 |
| `test_api_employment.py` | 搜索模糊匹配、年份过滤、趋势聚合、仅返回 published 数据 |
| `test_pipeline_fetcher.py` | 用本地 HTML fixture 模拟抓取（不联网） |
| `test_pipeline_extractor.py` | mock LLM API 返回，验证解析结果写入 DB + 状态流转 |
| `test_pipeline_review.py` | 状态流转 pending → parsed → reviewed → published |

### 6.3 前端测试

- 手动浏览器验证搜索流程、三块卡片渲染、空结果提示、跳转衔接
- `npm run build` 通过即视为前端测试通过

### 6.4 数据准确性抽检

- 每篇报告解析后，对比原始报告中 3 个关键数字（总人数、就业率、top1 雇主）
- 偏差 >5% 的标记为 `failed`，调整 prompt 后重新解析

---

## 7. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| LLM API | 智谱 GLM-4 / OpenAI GPT-4o | 智谱国内访问快、成本低；OpenAI 备选 |
| HTML 解析 | BeautifulSoup4 | 已有依赖基础，轻量 |
| PDF 解析 | pdfplumber | 表格提取能力强 |
| CLI 框架 | Click | 轻量，FastAPI 生态友好 |
| 配置 | `.env` 新增 `LLM_API_KEY` / `LLM_MODEL` / `LLM_BASE_URL` | 复用现有 pydantic-settings |
| HTTP 请求 | httpx | 异步支持，FastAPI 已有依赖传递 |

### 7.1 配置变更

`backend/app/config.py` 新增字段：
```python
LLM_API_KEY: str = ""
LLM_MODEL: str = "glm-4"
LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
```

---

## 8. 实施任务拆分

按 TDD 原则，每个任务先写测试再写实现：

| 任务 | 内容 | 依赖 |
|------|------|------|
| T1 | 数据模型：School / ReportRecord / EmploymentData + 迁移 | 无 |
| T2 | 管道 fetcher：HTML/PDF 抓取 + robots.txt 检查 | T1 |
| T3 | 管道 extractor：LLM 解析 + prompt 模板 + 状态流转 | T1 |
| T4 | 管道 review/publish：CLI 命令 + 状态流转 | T1 |
| T5 | 搜索 API：4 个端点 + service 层 | T1 |
| T6 | 前端搜索页 + 结果页 + 三块可视化卡片 | T5 |
| T7 | 前端导航更新 + Dashboard 衔接卡片 | T6 |
| T8 | 种子数据：配置 3 所标杆高校 + 跑通全管道 | T2,T3,T4 |

---

## 9. 合规与安全

1. **仅采集公开聚合统计数据**：就业率、流向分布、雇主名单，不采集可识别个人的微观数据
2. **遵守 robots.txt**：爬取前检查，被禁止的路径不访问
3. **控制请求频率**：间隔 3-5 秒，避免对高校网站造成压力
4. **注明数据来源**：每条数据关联 `source_url`，前端展示时显示来源
5. **不商业再分发**：数据仅用于平台内展示，不导出/售卖
6. **LLM API Key 安全**：仅存于 `.env`，不硬编码，不提交到 git

---

## 10. 验收标准

1. `python -m pipeline fetch --school tsinghua --year 2024` 能成功下载报告并存入 DB
2. `python -m pipeline extract --report-id <uuid>` 能通过 LLM 解析出结构化数据
3. `python -m pipeline review/publish` 能完成状态流转
4. `GET /api/employment/search?school=清华&major=机械` 返回正确的去向分布+排名+趋势
5. 前端 `/explore` 页面能搜索并展示三块可视化卡片
6. 至少 3 所学校 × 3 个专业 × 2 年的种子数据入库且已发布
7. 所有后端测试通过，前端构建通过
