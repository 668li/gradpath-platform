# Tasks 002：爬虫地基施工清单

- [ ] T0 环境销账：pip install trafilatura；pytest --collect-only 0 error
- [ ] T1 删除 G1 假爬虫三件套（scoreline×2/admission_ratio）+ grad/__init__ 修正 + collect
- [ ] T2 删除 G2 real_data/ 全目录+嵌套 dup（删前 grep from app.crawlers.real_data == 0）+ collect
- [ ] T3 删除 G3 career/（同步删除点）+ G5 research 三文件 + G6 reports 三文件+__init__ + collect
- [ ] T4 删除 G4 grad 8 个 RETIRED 大文件 + collect；全库 grep 退役名残留=0
- [ ] T5 transport.py（FetchResult/令牌桶/错误分类/robots/SSRF/红线索承）+ BaseCrawler._request 委托 + real_data_crawler 改造
- [ ] T6 守卫测试 test_transport_guard.py（裸外发请求零容忍）
- [ ] T7 迁移：t_crawler_source_state + t_external_research_item.data_origin/fetch_evidence + legacy 回填；模型列
- [ ] T8 store_research_items 三态强制（fetched 缺证据拒收/legacy 拒收）+ 8 个 call site 显式 data_origin + test_store_evidence_gate.py
- [ ] T9 BaseCrawler 生命周期接 state 表（游标读写/consecutive_fails）+ official_announce 基线迁 cursor
- [ ] T10 心跳统一钩子（10 源全覆盖，删 eol 手写段）+ 隔离判据 + 调度跳过 + admin unisolate 端点
- [ ] T11 sources/*.yaml（10 线）+ line_registry.py（白名单硬闸/cron/window 校验）+ DEFAULT_DAILY_SCHEDULES 改 yaml 生成（cron 逐字不变）
- [ ] T12 test_line_contract.py + test_crawler_source_state.py + test_heartbeat_coverage.py
- [ ] T13 eol_kaoyan 解析纯函数化 + 录制 2 样本 fixture + test_eol_parser_fixture.py
- [ ] T14 test_foundation_contract_drill.py（虚构源全链演练+坏样本负例）
- [ ] T15 全量 pytest 绿 + pre-commit --all-files（add 全部被 hook 改动文件）+ 显式路径 commit
- [ ] T16 gp-preflight 四闸 → bundle → scp → update_from_bundle.sh → HTTPS 冒烟（registry==10/迁移 current/三态列在场）
- [ ] T17 反思三问入记忆 + 交接快照更新
