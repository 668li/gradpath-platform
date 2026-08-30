# 数据线现状与修理决策（2026-08-29）

对 🟡 一次性存量 / 🔴 零产出数据线的第一性原理复盘与修理记录。
配套代码改动：`EMBEDDING_MODEL` 配置化、`bilibili_research` 周调度、
`vectorize_data.py --export` + `import_embeddings_jsonl.py`、rag_engine source_table 映射修复。

## 各线裁决

| 线 | 状态 | 裁决 | 依据 |
|---|---|---|---|
| rsshub_research / eol_kaoyan / official_announce | 🟢 每日调度中 | 保持 | 生产 8-29 启动调度，首跑 8-30 凌晨，之后每日自动 |
| bilibili_research | 🟡 一次性存量 | **已修**：加入每周一 03:00 调度 | 14 关键词 × 2 页自动增量，白名单内，yaml 本意 weekly 但调度器只认 DEFAULT_DAILY_SCHEDULES |
| web_article_research | 🟡 一次性存量 | 不调度，保留为按需工具 | 该爬虫吃 config.urls 种子列表，无种子时 fetch=0，排班=空转；常态化源已由 RSSHub 覆盖 |
| 职位表/薪资/公司/导师/院校线 | 🟡 一次性存量 | 不自动更新 | 年度/周期性官方发布（职位表每年 10 月中），定时抓是伪需求；正确姿势=发布日用 import_position_xlsx.py + yaml 重导 |
| yanzhao（预置招生数据） | 🟢 已在业务表 | 不重跑 | grad_school_intel 已覆盖 90 校 280 组合、grad_yanzhao_programs 150 条；重跑只会往审核队列塞重复项 |
| tieba/zhihu | 🔴 WAF 拦截 | 放弃（合规红线：不绕 WAF） | 知乎 3 条全拒、贴吧 0 条，对抗式审查确认绕过违反项目红线 |
| career/civil 旧爬虫 | 🔴 合成数据生成器 | 保持封死不删 | 用户红线：不删爬虫脚本；白名单机制已保证它们不可执行 |
| 就业报告管道 pipeline/ | 🔴 从未跑过 | **明确搁置**，启用条件见下 | 需 LLM Orchestrator（6 周冻结期）+ 学校级批量抓取；macro 就业面已由 market_data 1217 条覆盖 |
| 向量化 / RAG | 🔴 0 语料 | **已修**（分两步） | 见下 |

## 向量化/RAG：已做与待启用

已做（本次）：
1. `app.config.EMBEDDING_MODEL` 配置化，默认 **BAAI/bge-small-zh-v1.5**（512 维，2核4G CPU 可负担；
   原 bge-large-zh 在生产容器必然 OOM）。
2. 本地全量向量化 → `vectorize_data.py --export` → `import_embeddings_jsonl.py` 导入生产
   document_embeddings（服务器不装 torch）。
3. 修复 rag_engine `_search_semantic` 的 source_table 单复数映射 bug
   （vectorize 写 `experience_post`，映射表只有 `experience_posts`，语义结果此前会被静默丢弃）。

待启用（语义检索真正生效还需三步，等维护窗口）：
1. 生产 DB 镜像换 `pgvector/pgvector:pg16`（现 postgres 镜像无 vector 扩展，`CREATE EXTENSION` 不可用），
   dockerhub 拉镜像需走镜像源；compose 改 image + 数据卷保留。
2. backend 容器加 `sentence-transformers` 依赖（torch CPU 轮子 ~200MB，构建变慢）+
   `HF_ENDPOINT=https://hf-mirror.com` 环境变量供首次查询时下载模型（bge-small ~100MB）。
3. 重启后验证：`GET /api/rag/search?query=考研复试`，日志无 "semantic search unavailable" 即生效。

在此之前 `/api/rag/search` 走关键词降级路径（已在工作），前端当前无页面调用 RAG，无用户可见影响。

## 明天（2026-08-30）要做的事

- 检查生产 `crawler_runs`：eol/official_announce 02:00、rsshub 02:30、下周一 bilibili 03:00 首跑是否成功。
- 审掉 `t_review_queue_item` 积压的 51 条 PENDING（管理端 /api/admin/research-queue）。
