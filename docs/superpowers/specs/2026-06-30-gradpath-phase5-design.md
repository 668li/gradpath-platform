# Phase 5：统一数据源接入与智能路由

## 概述

扩展现有就业数据管道，支持四种数据源接入方式（PDF 解析、文件上传、外部 API 对接、扩展爬虫覆盖），通过智能路由自动识别内容类型并分发到对应的文本提取器，提取的纯文本统一进入已有的 LLM 结构化解析流程。同时提供管理员前端管理页面，实现全流程可视化管理。

**目标**：用户只需提供 URL 或上传文件，系统自动识别格式、提取文本、LLM 解析为结构化就业数据，无需手动判断文件类型。

## 背景

Phase 2 管道仅支持 HTML 爬虫抓取 + LLM 解析，`ReportRecord.raw_pdf_path` 字段已预留但未实现。当前管道存在以下局限：

- 仅能处理 HTML，无法解析 PDF/Excel 格式的就业报告（大量高校发布 PDF 版）
- 仅能通过 CLI 手动触发，无 API 接口，无前端管理界面
- 仅配置 10 所 985 高校，扩展新数据源需修改代码
- 无文件上传入口，无法处理无法爬取的高校

## 整体架构

```
                    ┌─────────────────────────────┐
                    │      接入层 (Ingestion)      │
                    │   POST /api/pipeline/ingest  │
                    │   url / file / api_source    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    智能路由 (Router Agent)    │
                    │  确定性规则优先，LLM 兜底     │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
     ┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
     │ HTML 提取器      │  │ PDF 提取器      │  │ Excel/CSV 提取器│
     │ (BeautifulSoup) │  │ (PyMuPDF)      │  │ (openpyxl)     │
     └────────┬────────┘  └───────┬────────┘  └───────┬────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   LLM 结构化解析器            │
                    │   (已有 extractor.py)        │
                    │   纯文本 → JSON → EmpData    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   ParseStatus 状态机          │
                    │   pending → parsed →         │
                    │   reviewed → published       │
                    └─────────────────────────────┘
```

## 数据模型

### ReportRecord 扩展

新增两个枚举和三个字段：

```python
class SourceType(str, enum.Enum):
    crawl = "crawl"      # 爬虫抓取
    upload = "upload"    # 文件上传
    api = "api"          # 外部 API 对接

class ContentType(str, enum.Enum):
    html = "html"
    pdf = "pdf"
    excel = "excel"
    csv = "csv"
    json = "json"
```

`ReportRecord` 新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_type` | `Enum(SourceType)` | 数据来源类型，默认 `crawl` |
| `content_type` | `Enum(ContentType) \| None` | 路由识别后的内容类型 |
| `file_path` | `String(500) \| None` | 上传文件存储路径（替代原 `raw_pdf_path`） |

`raw_html` 字段保留，语义扩展为"提取后文本"（HTML 原文或提取器输出的纯文本）。原 `raw_pdf_path` 字段保留兼容但不再使用（新数据写入 `file_path`）。

### DataSource 模型（新增）

存储可复用的外部 API 数据源配置：

```python
class DataSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="api")  # api / crawl
    api_url: Mapped[str | None] = mapped_column(Text)
    api_key: Mapped[str | None] = mapped_column(Text)  # 明文存储（示例项目，生产环境应加密）
    data_mapping: Mapped[dict | None] = mapped_column(JSONB)  # 字段映射规则
    is_active: Mapped[bool] = mapped_column(default=True)
```

`data_mapping` 示例：
```json
{
  "majors_path": "data.majors",
  "field_map": {
    "major_name": "name",
    "employment_rate": "employment",
    "further_study_rate": "further_study"
  }
}
```

### User 模型扩展

新增 `is_admin` 字段：

```python
is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
```

种子脚本中将 `test@test.com` 用户设为管理员。

## API 设计

所有 pipeline API 需管理员认证（`is_admin=True`）。

### 接入端点

`POST /api/pipeline/ingest` — 统一接入入口，支持三种模式：

**模式一 — URL 抓取**：
```json
{
  "source_type": "crawl",
  "school_slug": "tsinghua",
  "year": 2024,
  "url": "https://career.tsinghua.edu.cn/..."
}
```
复用已有 `fetcher.py` 的 HTTP 逻辑抓取内容，`source_type=crawl`。

**模式二 — 文件上传**：
multipart form-data，字段：
- `file`：文件二进制（支持 .pdf/.xlsx/.csv）
- `school_slug`：学校 slug
- `year`：年份

文件保存到 `backend/uploads/{school_slug}_{year}_{timestamp}.{ext}`，`source_type=upload`。

**模式三 — API 对接**：
```json
{
  "source_type": "api",
  "school_slug": "tsinghua",
  "year": 2024,
  "api_source_id": "uuid-of-datasource"
}
```
从 `DataSource` 读取配置，调用外部 API 拉取数据，`source_type=api`。

接入后创建 `ReportRecord`（状态 `pending`），触发路由 → 提取 → LLM 解析流程。如果整个流程同步完成，返回报告详情；如果文件较大需要异步处理，返回 `pending` 状态供前端轮询。

**同步处理策略**：鉴于就业报告通常不大（HTML < 1MB，PDF < 5MB），采用同步处理。LLM 解析超时 60 秒，总超时约 90 秒。如果 LLM 未配置（`LLM_API_KEY` 为空），报告保持 `pending` 状态，返回报告 ID 供后续 CLI 解析。

### 报告管理端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/pipeline/reports` | GET | 报告列表（支持 `status` 筛选、`page`/`page_size` 分页） |
| `/api/pipeline/reports/{id}` | GET | 报告详情（含解析结果 EmploymentData 预览） |
| `/api/pipeline/reports/{id}` | DELETE | 删除报告及其关联 EmploymentData |
| `/api/pipeline/reports/{id}/reparse` | POST | 重新解析（从已有文本重新跑 LLM） |
| `/api/pipeline/reports/{id}/publish` | POST | 发布报告（状态 → `published`） |

**报告列表响应**：
```json
{
  "items": [
    {
      "id": "uuid",
      "school_name": "清华大学",
      "year": 2024,
      "source_type": "upload",
      "content_type": "pdf",
      "parse_status": "parsed",
      "parse_error": null,
      "parsed_at": "2026-06-30T12:00:00Z",
      "created_at": "2026-06-30T11:00:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

**报告详情响应**：在列表基础上增加 `employment_data` 数组（解析出的专业数据预览）。

### 数据源配置端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/pipeline/sources` | GET | 数据源列表 |
| `/api/pipeline/sources` | POST | 新建数据源 |
| `/api/pipeline/sources/{id}` | PUT | 更新数据源 |
| `/api/pipeline/sources/{id}` | DELETE | 删除数据源 |

## 智能路由

`pipeline/router.py`，两步判断：

### 步骤 1 — 确定性判断（优先）

根据文件扩展名、Content-Type、URL 后缀判断：

| 信号 | 判定类型 |
|------|---------|
| `.pdf` / `application/pdf` | `pdf` |
| `.xlsx` / `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` / `application/vnd.ms-excel` | `excel` |
| `.csv` / `text/csv` | `csv` |
| `.json` / `application/json` | `json` |
| `http(s)://` URL 无文件后缀 | `html` |

### 步骤 2 — LLM 兜底（仅当步骤 1 无法判断）

取内容前 500 字符，调用轻量 LLM：

```
判断以下内容的文件类型，只返回一个词：html / pdf / excel / csv / json
内容片段：{preview}
```

如果 LLM 调用失败，默认按 `html` 处理，`parse_error` 记录警告。

### 设计理由

90% 以上场景可通过扩展名/MIME 确定，LLM 仅处理无扩展名的裸 URL 或二进制内容嗅探，避免不必要开销。

## 文本提取器

四个提取器统一接口：

```python
@dataclass
class ExtractResult:
    text: str                    # 提取的纯文本
    content_type: ContentType    # 实际类型
    metadata: dict               # 辅助信息（页数/sheet名/行数等）
```

### html_extractor.py

从现有 `extractor.py` 的 `_clean_html()` 提取为独立模块。BeautifulSoup 清洗 → 纯文本，保留表格结构。无新依赖。

### pdf_extractor.py

用 PyMuPDF（`fitz`）：
- 逐页提取文本，合并为全文
- 检测表格区域（`page.find_tables()`），表格部分转为 markdown 表格格式
- 超长 PDF（>50 页）截断前 50 页
- 新依赖：`pymupdf`

### excel_extractor.py

用 openpyxl：
- 逐 sheet 读取，每个 sheet 转为 markdown 表格
- 跳过空 sheet
- 单 sheet 最多 200 行
- 新依赖：`openpyxl`

### csv_extractor.py

无新依赖：
- 直接读取文本
- 检测分隔符（逗号/制表符/分号）
- 转为 markdown 表格格式

### 提取后流程

提取的纯文本存入 `ReportRecord.raw_html`（语义扩展），`content_type` 记录路由结果。文本进入已有 `extractor.py` 的 `call_llm()` → JSON → `EmploymentData` 入库。

## 前端管理页

### 路由结构

| 路由 | 页面 | 说明 |
|------|------|------|
| `/pipeline` | 数据源总览 | 报告列表 + 统计 + 状态筛选 |
| `/pipeline/ingest` | 接入新数据 | 三种模式 Tab 切换 |
| `/pipeline/sources` | API 数据源配置 | DataSource CRUD |

### 侧边栏导航

新增「数据管道」入口，仅管理员可见（前端根据用户 `is_admin` 字段控制显示）。

### 总览页 `/pipeline`

- 顶部统计卡片：总报告数、已发布、待审核、失败数
- 状态筛选 Tab：全部 / pending / parsed / failed / reviewed / published
- 报告列表表格：学校、年份、来源类型、内容类型、状态徽章、操作按钮（查看/重新解析/发布/删除）
- 分页（每页 20 条）

### 接入页 `/pipeline/ingest`

Tab 切换三种模式：
- **URL 抓取**：学校下拉选择、年份输入、URL 输入框、提交按钮
- **文件上传**：学校下拉、年份、文件拖拽区（.pdf/.xlsx/.csv）、提交按钮
- **API 对接**：学校下拉、年份、数据源下拉选择、提交按钮

提交后跳转到总览页，新报告高亮显示。

### 数据源配置页 `/pipeline/sources`

- 数据源列表（名称、类型、URL、状态）
- 新增/编辑表单（名称、API URL、API Key、字段映射规则 JSON 编辑器、启用开关）

## 错误处理

### 接入阶段

| 错误场景 | 处理 |
|----------|------|
| URL 抓取失败（HTTP 非 200/超时） | `ReportRecord` 状态 `failed`，`parse_error` 记录原因 |
| 文件上传格式不支持 | API 返回 400 + 错误消息 |
| 文件过大（>20MB） | API 返回 413 + 错误消息 |
| API 对接认证失败 | 状态 `failed`，记录错误 |
| 学校不存在 | API 返回 404 |
| 报告已存在（同校同年） | API 返回 409，提示使用重新解析 |

### 路由阶段

| 错误场景 | 处理 |
|----------|------|
| 无法识别类型 | 默认按 HTML 处理，`parse_error` 记录警告 |
| LLM 路由调用失败 | 同上兜底 |

### 提取阶段

| 错误场景 | 处理 |
|----------|------|
| PDF 损坏/加密 | 状态 `failed`，错误「PDF 文件无法读取」 |
| Excel 格式异常 | 状态 `failed`，错误「Excel 文件格式无效」 |
| 提取文本为空 | 状态 `failed`，错误「未提取到有效内容」 |

### 解析阶段

复用已有 `extractor.py` 错误处理：LLM 返回无效 JSON / 调用失败 → 状态 `failed`。

## 文件存储

上传文件存储在 `backend/uploads/` 目录，文件名格式 `{school_slug}_{year}_{timestamp}.{ext}`。`.gitignore` 排除该目录。路径记录在 `ReportRecord.file_path`。

## 测试策略

### 后端测试（pytest）

| 测试文件 | 覆盖范围 | 预估测试数 |
|----------|---------|-----------|
| `test_pipeline_router.py` | 确定性路由（扩展名/MIME）、LLM 兜底（mock）、无法识别时默认 HTML | ~8 |
| `test_pipeline_extractors.py` | HTML 清洗、PDF 提取（fixture PDF）、Excel 提取（fixture xlsx）、CSV 提取、空文件/损坏文件错误 | ~10 |
| `test_api_pipeline.py` | 接入端点三种模式、报告列表/详情/删除/重新解析/发布、管理员权限校验、文件上传 multipart、文件大小限制 | ~15 |
| `test_api_sources.py` | DataSource CRUD、启用/禁用 | ~6 |

### 测试 Fixture

- `tests/fixtures/sample_report.pdf`：2 页测试 PDF，含表格
- `tests/fixtures/sample_report.xlsx`：2 sheet 测试 Excel
- `tests/fixtures/sample_report.csv`：测试 CSV
- `tests/fixtures/sample_report.html`：测试 HTML

LLM 调用全部 mock（`monkeypatch` 替换 `call_llm`），路由 LLM 同理 mock。

### 前端验证

E2E 验证管理页渲染、三种接入模式表单提交、报告列表筛选。

## 种子数据

`pipeline/seed_sources.py`：预置 2 个外部 API 数据源配置（示例性质，`is_active=False`）：
- 「教育部高校毕业生就业统计」示例 API
- 「麦可思就业数据」示例 API

已有的 `seed.py` 10 校 3 年种子数据保持不变。

## 新增依赖

- `pymupdf`（PDF 提取）
- `openpyxl`（Excel 提取）
- `python-multipart`（文件上传，FastAPI multipart 支持）

## 不做的事（YAGNI）

- 不做定时调度/定时抓取（保持 CLI/API 手动触发）
- 不做 OCR（图片型 PDF 未来再加）
- 不做数据源健康检查/监控
- 不做版本控制/报告历史对比
- 不做 API 数据源自动字段映射推断（mapping 规则手写 JSON）
- 不做异步任务队列（同步处理，超时返回 pending 状态）
