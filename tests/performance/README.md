# k6 性能压测脚本

GradPath 决策助手（FastAPI 后端 + Next.js 前端）的 k6 负载压测套件，目标承载 1000+ 用户流畅访问。

## 环境要求

- **k6** ≥ 0.50（安装：`choco install k6` 或下载 [releases](https://github.com/grafana/k6/releases)）
- **后端服务**：FastAPI 监听 `http://localhost:8000`（默认）
- **测试账号**：需先执行 `seed-test-users.js` 注册测试账号

```powershell
# 验证 k6 安装
k6 version

# 验证后端可用
curl http://localhost:8000/health
```

## 脚本清单

| 脚本 | 类型 | VU | 时长 | 阈值 | 用途 |
|---|---|---|---|---|---|
| `smoke.js` | 冒烟 | 3 | 30s | p95<500ms, fail<1% | 验证服务可用、公开端点正常 |
| `load.js` | 负载 | 50→200 | 5m | p95<2s, p99<5s, fail<5% | 模拟日常峰值，验证稳定性 |
| `stress.js` | 极限 | 200→500→1000 | 11m | 分组 p95<2~5s, fail<10% | 找系统瓶颈与吞吐拐点 |
| `spike.js` | 突发 | 0→500 | 1m40s | p95<5s, fail<20% | 模拟推送引流瞬时高峰 |
| `ai-endpoint.js` | AI 专项 | 20 | 2m | p95<30s, fail<30% | 压测 LLM 调用链路与熔断器 |
| `seed-test-users.js` | 数据准备 | 1 | 变长 | 无 | 批量注册测试账号（前置） |

## 执行命令

### 0. 准备测试账号（首次必做）

```powershell
# 默认注册 10 个 load + 10 个 test 账号，约 7 分钟（受 register 限速 3/min 约束）
k6 run seed-test-users.js

# 注册 100 个（需先临时调高 register 限速，见下文"限速处理"）
k6 run -e USER_COUNT=100 -e REGISTER_INTERVAL=1 seed-test-users.js
```

### 1. 冒烟测试

```powershell
k6 run smoke.js
k6 run -e BASE_URL=http://localhost:8000 smoke.js
```

### 2. 负载测试

```powershell
k6 run load.js
```

### 3. 极限压测

```powershell
k6 run stress.js
```

### 4. 突发流量测试

```powershell
k6 run spike.js
```

### 5. AI 端点专项

```powershell
# 需确保后端 LLM_API_KEY 已配置
k6 run ai-endpoint.js
```

### 6. 一键全量压测

```powershell
.\run-all.ps1
.\run-all.ps1 -BaseUrl http://localhost:8000
```

结果输出到 `results/{yyyyMMdd-HHmmss}/` 目录，每个脚本生成 `.json`（机器可读）+ `.log`（终端输出）。

## 端点路径说明

> **重要**：任务描述中部分端点路径与后端实际实现不一致，脚本已修正为实际路径。

| 任务描述 | 实际路径 | 说明 |
|---|---|---|
| `GET /health` | `GET /health` | 健康检查 |
| `GET /api/schools` | `GET /api/employment/schools` | 院校搜索（无独立 `/api/schools`） |
| `GET /api/posts/public` | `GET /api/posts/public` | 社区帖子 |
| `GET /api/employment/schools` | `GET /api/employment/schools` | 就业院校数据（不接受 `limit` 参数） |
| `POST /api/auth/register` | `POST /api/auth/register` | 注册，返回 201，限速 3/min |
| `POST /api/auth/login` | `POST /api/auth/login` | 登录，返回 `access_token` + `refresh_token`，限速 5/min |
| `GET /api/dashboard` | `GET /api/dashboard/overview` | **已修正**：实际路由前缀 + `/overview` |
| `GET /api/career-intel/intel` | `GET /api/career-intel/intel/list` | **已修正**：实际是 `/intel/list` |
| `GET /api/mentors` | `GET /api/mentors/personas` 或 `/kaoyan-mentors` | 实际无裸 `/api/mentors` GET |
| `GET /api/decisions` | `GET /api/decisions` | 决策列表 |
| `POST /api/ai/decision-advice` | `POST /api/ai/decision-advice` | AI 决策指导，限速 10/min/用户 |

## 限速处理（关键）

后端 `backend/app/api/auth.py` 与 `backend/app/api/ai.py` 配置了基于 IP/用户的限速，压测时需要临时调整，否则 k6 VU 会大量收到 429：

| 端点 | 限速 | 影响 | 测试期建议 |
|---|---|---|---|
| `/api/auth/register` | 3/min/IP | `seed-test-users.js` 慢 | 调到 `200/minute` 或注释 `@limiter.limit` |
| `/api/auth/login` | 5/min/IP | `load/stress/spike` 大量 429 | 调到 `1000/minute` 或注释 |
| `/api/ai/decision-advice` | 10/min/用户 | `ai-endpoint.js` 单账号限速 | 已用 20 账号轮换规避；如仍不够，调到 `100/minute` |

**调整方法**（临时，测试后恢复）：

```python
# backend/app/api/auth.py
@router.post("/login", response_model=TokenResponse)
@limiter.limit("1000/minute")  # 测试期临时调高，原值 "5/minute"
def login_endpoint(...):
```

或测试环境通过环境变量 `RATE_LIMIT_ENABLED=false` 关闭（若代码支持）。

## 如何解读结果

k6 运行结束会输出核心指标：

```
✓ 'login 200' - 95% 成功率
✓ 'dashboard 200' - 92% 成功率

http_req_duration..........: avg=320ms p(95)=890ms p(99)=1.8s
http_req_failed............: 4.5% (429 限速为主)
iterations.................: 12500  41.6/s
vus........................: 200
```

### 关键指标

| 指标 | 含义 | 健康阈值 |
|---|---|---|
| `http_req_duration` p(95) | 95% 请求的响应时间 | < 2s（负载）/ < 5s（极限） |
| `http_req_duration` p(99) | 99% 请求的响应时间 | < 5s（负载）/ < 10s（极限） |
| `http_req_failed` | 非 2xx 比例 | < 5%（负载）/ < 10%（极限） |
| `iterations` rate | 每秒完成迭代数（吞吐） | 越高越好，关注拐点 |
| `vus` | 当前虚拟用户数 | 应与 stages 配置一致 |
| `http_req_blocked` | 请求被阻塞时长（连接池等待） | < 100ms，高则连接池不足 |
| `http_req_connecting` | TCP 连接建立时长 | < 50ms，高则后端 accept 慢 |

### 阈值通过/失败

k6 退出码：
- `0` = 所有阈值通过
- `1` = 有阈值失败（但仍输出完整结果）

CI 集成时用退出码判断是否阻断流水线。

## 性能基线

**首次运行结果应记录为基线**，后续回归对比。基线模板（复制到 `results/baseline.md`）：

```markdown
# 性能基线 - {日期}

## 环境信息
- 后端：FastAPI {版本}，Python {版本}
- 数据库：PostgreSQL {版本}，连接池 {size}
- 部署：本地 / Docker / K8s
- 硬件：CPU {核} / RAM {GB}

## 基线指标

### smoke (3 VU, 30s)
- http_req_duration p(95): ___ ms
- http_req_failed: ___ %
- iterations/s: ___

### load (50→200 VU, 5m)
- http_req_duration p(95): ___ ms
- http_req_duration p(99): ___ ms
- http_req_failed: ___ %
- 峰值吞吐: ___ iter/s
- 峰值 RPS: ___

### stress (1000 VU 峰值)
- 拐点 VU 数: ___ （吞吐开始下降的 VU）
- 拐点吞吐: ___ iter/s
- 1000 VU 下 p(95): ___ ms
- 1000 VU 下失败率: ___ %
- 首个 5xx 出现的 VU: ___

### spike (500 VU 瞬时)
- 峰值 p(95): ___ ms
- 恢复时间（降到 0 后 p95 回正常）: ___ s
- 5xx 数量: ___

### ai-endpoint (20 VU, 2m)
- p(95): ___ s
- 200 成功率: ___ %
- 429/503 降级率: ___ %
```

## 瓶颈定位指引

### 1. 响应时间随 VU 线性增长 → 后端 CPU 瓶颈

**症状**：`http_req_duration` 与 `vus` 同步上升，`http_req_blocked` 低。
**定位**：
- `docker stats` / 任务管理器看后端进程 CPU%
- `py-spy top --pid <backend_pid>` 看 Python 热点函数
- 检查是否有 N+1 查询、同步阻塞调用

**优化**：
- 加缓存（Redis）—— `/api/employment/schools` 已配置 `max-age=3600`
- 异步化耗时操作（Celery 任务）
- 横向扩容（uvicorn workers）

### 2. `http_req_blocked` 高 → 连接池不足

**症状**：`http_req_blocked` > 100ms，`http_req_connecting` 低。
**定位**：k6 复用连接池打满，后端 worker 不够。
**优化**：
- 后端：增加 uvicorn workers（`--workers 4`）
- 数据库：调大连接池 `DATABASE_POOL_SIZE`
- k6：保持默认（每 VU 一个连接）

### 3. 失败率随 VU 飙升 → 限速或资源耗尽

**症状**：`http_req_failed` 在某个 VU 数后突然飙升。
**定位**：
- 看响应码分布：429 = 限速，502/503 = 后端崩溃，504 = 超时
- 429：调高限速（见"限速处理"）
- 502/503：看后端日志，可能 OOM 或 worker 崩溃
- 504：看 `http_req_duration` 是否接近 60s（k6 默认超时）

### 4. 数据库瓶颈

**症状**：`/api/career-intel/intel/list` 等 DB 重查询 p95 远高于其他端点。
**定位**：
```sql
-- PostgreSQL 慢查询
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
```
**优化**：
- 加索引（检查 EXPLAIN ANALYZE）
- 加分页（cursor pagination）
- 加物化视图或缓存

### 5. AI 端点瓶颈

**症状**：`ai-endpoint.js` p95 > 30s，或 503 比例高。
**定位**：
- 看熔断器状态：`AICircuitBreakerOpenError` 日志
- 看 LLM 配额：`AILLMQuotaExceeded` 日志
- 看 LLM 上游延迟：`httpx.TimeoutException`

**优化**：
- 调整熔断阈值（`AICircuitBreaker` 配置）
- 增加 LLM 调用并发上限
- 引入请求队列（Celery）异步化

### 6. 突发流量恢复慢

**症状**：`spike.js` 降到 0 VU 后，后续请求仍慢。
**定位**：后端 worker 堆积、DB 连接未释放、缓存击穿。
**优化**：
- 配置 `max_workers` 上限 + 队列
- 启用请求超时 + 熔断
- 预热缓存（启动时加载热点数据）

## 目录结构

```
tests/performance/
├── smoke.js              # 冒烟测试
├── load.js               # 负载测试
├── stress.js             # 极限压测
├── spike.js              # 突发流量测试
├── ai-endpoint.js        # AI 端点专项
├── seed-test-users.js    # 测试账号注册
├── run-all.ps1           # 全量压测编排
├── README.md             # 本文档
└── results/              # 压测结果（运行后生成）
    └── {yyyyMMdd-HHmmss}/
        ├── smoke.json
        ├── smoke.log
        ├── load.json
        ├── load.log
        └── ...
```

## 常见问题

### Q: k6 报错 `command not found`

A: Windows 上用 `choco install k6`，或下载 releases 解压后把 `k6.exe` 加入 PATH。

### Q: 所有 check 都失败，status=0

A: 后端未启动，或 BASE_URL 错误。先 `curl http://localhost:8000/health` 验证。

### Q: login 200 通过率很低

A: 登录限速 5/min/IP，多 VU 共享 IP 触发 429。见"限速处理"调高限速。

### Q: `group:::Dashboard` 阈值不触发

A: k6 嵌套 group 的 tag 是完整路径 `:::parent:::child`。本套件把 Dashboard/院校搜索/公司情报 设为顶层 group，tag 为 `:::Dashboard`，与阈值匹配。

### Q: AI 端点全部 503

A: LLM_API_KEY 未配置，或熔断器打开。检查后端日志 `AIServiceNotConfigured` / `AICircuitBreakerOpenError`。
