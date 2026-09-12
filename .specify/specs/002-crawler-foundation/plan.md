# Plan 002：爬虫地基实施设计

2026-09-12 ｜ 配套 spec.md ｜ 原则：收敛不是重写（BaseCrawler/store/crawler_runs 复用），框架一个不引，删除是收敛的一部分。

## 1. 六块落点（技术设计）

### FR1 统一传输层 → `app/crawlers/transport.py`（新，~200 行）

```python
@dataclass
class FetchResult:
    url: str; status_code: int; text: str; content: bytes
    fetched_at: datetime; sha256: str; elapsed_s: float

def fetch(url, *, crawler_name, is_file=False, timeout=30, headers=None) -> FetchResult
```

- httpx.Client（同步，Celery worker 语义）+ per-host 令牌桶（dict+Lock；静态 ≥0.5s / `is_file=True` ≥2s）。
- 复用 `url_safety`（SSRF）与 robots 检查（从 base_crawler 提取共用）；继承 `_REDLINE_HOSTS` 域名闸。
- 错误分类：4xx → `HttpFetchError` 不重试；429 → 停 20s 后报错（当天放弃语义由上层 run 控制）；5xx/网络错 → 指数退避重试 ≤3 次；无论成败返回/抛出都带证据。
- `BaseCrawler._request` 改为委托 `transport.fetch`，返回 httpx.Response（`.text/.status_code/.json` 与 requests 兼容面足够；逐调用点核对）。
- **守卫测试** `test_transport_guard.py`：遍历 `app/crawlers/**.py`，凡 `httpx.get|httpx.AsyncClient|requests.get|urlopen` 出现在 transport/base_crawler 之外即红（白名单：transport.py、base_crawler.py、crawl4ai_client.py）。

### FR2 声明式线契约 → `app/crawlers/sources/*.yaml` + `app/crawlers/line_registry.py`（新，~150 行）

- 一线一 yaml：`name/entry/schedule/budget{max_pages_per_run,min_interval_s}/sla_hours/window/crawler/target`。5 条在产调度线（eol_kaoyan 02:00、official_announce 每小时、rsshub 02:30、news_aggregates 04:00、bilibili 周一 03:00）+ 5 条手动线（schedule: null）。
- `load_lines()`：自动发现、cron 用 `APScheduler CronTrigger.from_crontab` 校验、`window: {start: MM-DD, end: MM-DD}` 格式校验、**name ∈ ALLOWED_CRAWLERS 硬闸**（越界 ValueError=加载即炸）。
- `api/crawlers.py`：`DEFAULT_DAILY_SCHEDULES` 改由 `load_lines()` 生成（job_id=`crawler_{name}`、cron 值与现状逐字一致）；`seed_default_schedules` 不变。
- 测试 `test_line_contract.py`：白名单 10 源人人有 yaml；yaml 名全部 ∈ 白名单；5 条 cron 与冻结值一致。

### FR3 状态表 → `app/models/crawler_state.py`（新）+ 迁移

```
t_crawler_source_state:
  source_name String(50) PK
  cursor JSONB null            # 增量游标（URL 集合/最新发布时间/etag）
  last_ok_at / last_run_at DateTime null
  consecutive_fails Int default 0
  isolated Bool default False; isolated_reason String(500) null
  updated_at DateTime
```

- BaseCrawler 运行生命周期接入：`_begin_run` 读状态行 → 成功写 `last_ok_at`+游标+清零 fails → 失败 `consecutive_fails+1`。
- official_announce 的 `_load_known_urls` 内存基线迁入 `cursor.known_urls`（cursor 为空时回退现查库，兼容首跑）。
- 迁移链在 prod head f1a3b5c7d9e2 之上追加；SQLite/Postgres 双兼容（JSONB 沿用 external_meta 先例）。

### FR4 三态证据 → 迁移 + `research_ingestion.py` 强制

- t_external_research_item 增列：`data_origin String(12)`、`fetch_evidence JSONB`；迁移内 `UPDATE ... SET data_origin='legacy' WHERE data_origin IS NULL`（存量冻结，蓝图 C5）。
- `store_research_items(..., data_origin=None)`：逐条 origin 解析（显式参 > item 字段 > 缺省 fetched）；**fetched 必带 `fetch_evidence{http_status,fetched_at,sha256}` 三齐全，缺一该条拒收**（计数+日志，不炸整批）；origin=legacy 拒收（新写入禁用）；curated/ugc 照实落列。
- 证据来源：transport.FetchResult → BaseCrawler 缓存 `last_fetch_evidence`，store 前由爬虫附着到 item；call site 逐一核对（seed/promote 等 8 处显式声明 data_origin，杜绝隐式 fetched 无证据）。
- 负例测试 `test_store_evidence_gate.py`：缺 sha256 → 拒；缺 fetched_at → 拒；origin=legacy → 拒；带全证据 → 落库且列可见。

### FR5 心跳全覆盖+自动隔离 → BaseCrawler 记账钩子

- 记账点（base_crawler CrawlerRun 落库处）统一追加 `record_heartbeat(source, ok, items)` upsert data_freshness；删除 eol_kaoyan_crawler.py:188-197 手写段。
- 隔离判据：`parse_fail_rate>0.3 且 items≥10` 或 `consecutive_fails≥2` → `state.isolated=True`+reason；调度入口（`_run_scheduled_crawler` 与手动 run.py）先查隔离位，隔离则跳过并写 freshness status='isolated'。
- 解除=显式：admin 端点 `POST /admin/crawlers/{name}/unisolate`（写审计日志）。
- 测试：10 源 run 后 freshness 必有行；连续 2 失败→隔离位真；调度跳过隔离源；stale 判定（last_ok_at 超 2×SLA）→ freshness 状态翻转（判据 3）。

### FR6 疫苗+虚构源演练

- eol_kaoyan 解析抽模块级纯函数 `parse_eol_html(html) -> list[dict]`；`curl` 实抓 2 个真实页面存 `tests/fixtures/eol_kaoyan/`，断言标题/链接/来源字段。
- `test_foundation_contract_drill.py`（判据 1+2）：测试内 demo 线 = 临时目录 yaml + 纯函数 parser + 2 录制样本：load_lines 过白名单闸（demo 名不在白名单应红→演示闸起作用，用假名断言 ValueError；合法演示用 monkeypatch 白名单）→ parse → 证据校验链；另含「坏样本」负例：结构漂移的 HTML 必须零产出/报错，不得静默成功。

### FR7 死重根除（删除清单，每组删前 grep 引用、删后 collect 绿）

| 组 | 内容 | 佐证 |
|---|---|---|
| G1 | grad/scoreline_crawler.py、scoreline_real_crawler.py、admission_ratio_crawler.py | R3 实锤字面量合成=命名造假；grad/__init__ 刻意不导入 |
| G2 | crawlers/real_data/ 全目录（~90 脚本，含 salary_expand `import random` 造假生成器）+ real_data/real_data/ 嵌套 dup | 孤儿一次性脚本；tests/fixtures/real_data **保留**（属在产 real_data 线） |
| G3 | crawlers/career/ 全目录 5 爬虫 | register 全注释 @RETIRED；boss/lagou WAF+ToS 红线 |
| G4 | grad/: dark_knowledge_crawler(29,630 行)、mentor_crawler(5,023)、mentor_review_aggregator(6,238)、forum_crawler、forum_experience_crawler、retest_experience_crawler、adjustment_crawler、adjustment_real_crawler、mentor_scraper | 全部 @RETIRED 2026-09-06 注释态 |
| G5 | research/: zhihu_research_crawler、tieba_research_crawler、v2ex_knowledge | 09-06 白名单下架；v2ex 核引用后删 |
| G6 | reports/: stats_importer（预置假版；真抓=stats_gongbao_scraper）、github_datasets、pdf_parser；同步 reports/__init__.py | RETIRED 注释自述 |

- **不删**：config/position_xlsx 归档管道（宪法 3）、tests/fixtures/**、registry 不变量测试、dark_knowledge push 读路径、gwy API（挂账）。
- 删除后退役名单语义不变：不变量测试的 retired 集合保留（文件没了更不可能复活）。

## 2. 对抗式审查（攻击本 plan）

| # | 攻击 | 判决 |
|---|---|---|
| A1 | 删 real_data/ 会断在产 real_data 线？ | 不成立：在产源是 grad/real_data_crawler.py（独立文件）；real_data/ 目录是一次性脚本堆。删前 grep `from app.crawlers.real_data` 全库为 0 才动刀 |
| A2 | DEFAULT_DAILY_SCHEDULES 改 yaml 生成会破坏 admin API/Redis jobstore 兼容 | 部分成立：job_id 与 cron 逐字不变（测试锁死），替换的只是常量来源；Redis 里既有 job 在 seed 时幂等重排 |
| A3 | 迁移双库兼容风险（SQLite dev / Postgres prod） | 成立：JSONB 列沿用 external_meta 先例；迁移前实测 prod alembic current，dev 库升级后跑全量 pytest 验证 |
| A4 | store 严格默认会误杀现有合法调用点 | 成立：实施时逐个核对 8 个 call site，curated 语义的（seed/promote）显式传 data_origin；任何拿不准的以「显式 curated」降级处理，不静默 fetched |
| A5 | _request 换 httpx 改变行为（超时/重试/响应属性） | 部分成立：签名兼容+test_base_crawler 回归+10 源 run 冒烟（TestClient 本地跑 real_data/eol 两源真实 run 验证证据链落列） |
| A6 | 隔离误伤（偶发失败停线） | 成立：阈值双条件（失败率>30% 需 ≥10 样本，或连续 2 run 失败）；隔离只跳调度不删数据；解除是显式动作 |
| A7 | 虚构源演练违反零造假红线 | 不成立：演练只存在于测试进程（与现有 46 个 fixture 同性质），不进白名单/库/调度；R1 已固化 |
| A8 | 删 stats_importer 影响 2027-02 统计公报重跑 | 不成立：真抓者是 stats_gongbao_scraper（RETIRED 注释自述），删前 grep 证实引用链 |
| A9 | 16 文件裸 httpx 只修 2 个，其余靠删除蒙混？ | 判决：16 个里 14 个在被删目录内（real_data/ 12 + career/ 2），改造对象仅 real_data_crawler.py 与 v2ex_knowledge.py（后者随 G5 删）——守卫测试防新增，不靠自觉 |
| A10 | 本地 trafilatura 缺失 20 个收集错误 → 「全绿」是假绿 | 成立：第一步 pip install trafilatura 销环境账，collect 0 error 是后续一切的前置闸 |

## 3. 施工顺序

1. 环境销账（trafilatura）→ collect 0 error
2. 删除批 G1→G6（每组 grep→删→__init__ 修正→collect）
3. transport.py + BaseCrawler 委托 + real_data_crawler 改造 + 守卫测试
4. 迁移（state 表+三态列+legacy 回填）→ 模型
5. store 三态强制 + 8 call site 显式化 + 负例测试
6. 心跳钩子+隔离+调度跳过+admin 解除端点
7. sources/*.yaml + line_registry + 调度切换 + 契约测试
8. eol fixture 疫苗 + 虚构源演练测试
9. 全量 pytest + pre-commit --all-files + commit（显式路径）
10. gp-preflight 四闸 → bundle 部署 → HTTPS 冒烟 → 反思入记忆
