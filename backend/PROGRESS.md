# 开工回执（2026-09-05）
- 理解目标：修 4 实锤缺陷（连击 UTC 日期基准/通知深链/完成幂等/爬虫调度时区）+ 2 边角（user_response strip / docs 度量口径），只动任务书白名单文件。
- 执行顺序：任务0核验 → 任务1连击换基准 → 任务2深链 → 任务3幂等 → 任务4时区 → 任务5边角 → 全量验收。
- 核验结果：基线 1750 passed / 0 failed / 0 skipped（≥1750 达标）；streak_service.py date.today() 计数=6 达标；app/utils 不存在 → 将新建目录+__init__.py。
- 最大风险：streak_service 的 6 处 date.today() 所在函数被大量既有测试直接调用，换 beijing_today() 后若既有测试断言"今天"用了本机本地日期之外的日期可能翻车；用参数注入（默认 beijing_today()）方式保既有测试兼容。

# 验收记录（2026-09-05 完工）
1. `py -3.13 -m pytest tests/ -q` 最终：**1760 passed, 0 failed, 0 skipped**（393.92s）。基线 1750 passed / 0 failed / 0 skipped → 新增 +10 ≥ +6，skipped 0→0 不增。
2. `grep -n "date.today()" app/services/streak_service.py` → 零输出（6 处已全部换为 beijing_today()，record_activity/_week_start 支持 today 参数注入）。
3. `grep -n "link: str | None = None" app/api/notifications.py` → 2 处（269 行 create_notification、290 行 push_notification）。
4. `grep -n "timezone=BEIJING_TZ" app/api/crawlers.py` → 1 处（613 行 seed_default_schedules 的 add_job）；reminder_service REMINDER_TZ 已改为 BEIJING_TZ 别名（对外名不变，test_reminder_d2.py 原断言未动全过）。
5. 改动文件清单：
   - 新增：app/utils/business_time.py、app/utils/__init__.py、tests/test_business_time.py（4 条）、tests/test_crawler_schedule_tz.py（2 条）、docs/度量口径.md
   - 修改：app/services/streak_service.py（6 处换基准+参数注入）、app/api/notifications.py（link 参数透传）、app/services/reminder_service.py（link="/micro-actions" + REMINDER_TZ 别名）、app/services/micro_action_service.py（complete/skip 幂等守卫 + user_response strip）、app/api/crawlers.py（add_job timezone）、tests/test_reminder_d2.py（+1 深链测试）、tests/test_micro_action.py（+3 幂等/strip 测试）、PROGRESS.md
6. 新增测试共 10 条：business_time 4 + crawler_schedule_tz 2 + reminder 深链 1 + 幂等/strip 3。
7. 度量口径 SQL 的 psql 实测：本仓库测试环境为 SQLite，未跑 psql 验证该 PostgreSQL 方言 SQL；表名以模型实测（notifications/micro_action_tasks/streak_records 均存在）。
8. 最大风险：连击基准从系统本地日期换成 Asia/Shanghai 日期——本机与生产 UTC 容器在北京时间 0-8 点的行为归日会变化（这正是修复目标）；若部署后 21:00 提醒与 02:00 爬虫 cron 的触发时刻与预期不符，优先查容器 tzdata 是否可用（ZoneInfo 依赖 tzdata 包，Windows/精简镜像需预装）。
9. 红线自检：未 skip/删/放松任何既有测试；无 git 操作；无数据迁移/UPDATE；未 mock datetime.now/date.today（全部参数注入）。
