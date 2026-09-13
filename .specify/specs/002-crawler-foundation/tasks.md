# Tasks 002：爬虫地基施工清单

- [x] T0 环境销账：pip install trafilatura（另补 celery）；collect 1894→0 error
- [x] T1 删除 G1 假爬虫三件套（scoreline×2/admission_ratio）+ grad/__init__ 修正 + collect
- [x] T2 删除 G2 real_data/ 全目录+嵌套 dup（删前 grep from app.crawlers.real_data == 0）+ collect
- [x] T3 删除 G3 career/（同步删除点）+ G5 research 三文件 + G6 reports 三文件+__init__ + collect
- [x] T4 删除 G4 grad 8 个 RETIRED 大文件 + collect；全库 grep 退役名残留=0；**意外收获**：civil/ 空壳与 scrapy_grad/ 死实验（侦察漏网）一并根除
- [x] T5 transport.py（FetchResult/令牌桶/错误分类/robots/SSRF/红线承袭）+ BaseCrawler._request 委托 + real_data_crawler 改造（研招网分支+预置补位同日根除）
- [x] T6 守卫测试 test_transport_guard.py（裸外发零容忍+红线域拒发负例）
- [x] T7 迁移 b8e4f2a6c9d3：t_crawler_source_state + data_origin/fetch_evidence + legacy 回填（生产实证 5316 行冻结）
- [x] T8 store_research_items 三态强制 + 8 个 call site 显式化 + test_store_evidence_gate.py（9 例）
- [x] T9 BaseCrawler 生命周期接状态表 + 证据两路统一（逐条盖章 OR 会话级 fetch_log，与信任锚 _fetch_log 融合为唯一留痕）
- [x] T10 心跳统一钩子（10 源全覆盖，删 eol 手写段）+ 隔离判据 + 调度/worker 双闸（fail-open）+ admin unisolate
- [x] T11 sources 线契约 10 yaml + line_registry（白名单硬闸/cron/window 校验）+ DEFAULT_DAILY_SCHEDULES 改 yaml 生成（cron 逐字不变）
- [x] T12 test_line_contract.py + test_crawler_source_state.py（调度跳过实证）+ 心跳覆盖
- [x] T13 eol_kaoyan 解析纯函数化 + 实录 2 样本 fixture（126KB/137KB）+ 疫苗测试
- [x] T14 test_foundation_contract_drill.py（虚构源全链+坏样本负例）
- [x] T15 全量绿（收敛树 1941 passed）+ pre-commit --all-files（含封印夹具字节冻结修复）+ 显式路径 commit ×3
- [x] T16 四闸（克隆内手动执行，preflight 脚本对克隆 ref 假阳已记录）→ bundle(/tmp 绝对路径) → 部署 a485baec → 迁移上产 → HTTPS 冒烟 + 生产不变量实证
- [x] T17 反思入记忆（crawler-foundation-002-deployed + batch-closing-actions-discipline）
