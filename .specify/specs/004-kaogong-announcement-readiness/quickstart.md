# Quickstart 004：验证手册

> 只做验证与演练，不含实现。命令一律从项目根/backend 目录按既有惯例执行。

## §1 探针 runbook（FR2 第一优先）— **09-14 已实测第一遍，结论见 `research.md` D4**

1. 候选入口（**09-14 实测后修订**；明细见 `research.md` D4）：
   - 灯塔-党建在线 **招考公告列表** `https://www.dtdjzx.gov.cn/web/dtdjzx/lygwyzkgg.html`（检测源；列表数据在 script 内，content_sha diff 可用）
   - 灯塔 **公告详情** `/web/dtdjzx/lygwyzkgg/{id}.html`（证据源；DOM 含标题+时间+来源）
   - ~~山东人事考试信息网（rsks.shandong.gov.cn）~~ → **死链（NXDOMAIN），移出清单**
   - 山东省人社厅 `hrss.shandong.gov.cn/channels/ch00330/`（纯静态可读✓，但非考录渠道，仅留档）
   - 第二线：`www.gov.cn`（可达✓；转登栏目待公告日实测）；scs 系（证书不匹配/WAF 挑战）**不可用，不绕过**；广东人事考试网（待探）
2. 每候选记录：HTTP 码 / 正文长度（trafilatura 抽取后）/ 是否 SPA 壳（<2KB）/ 日期串命中（归一化）。
3. **通过判据**：200 + 正文 ≥2KB + 日期串命中；**按证据闸谓词实测**（`require_evidence_fetch` 三条件；`html_to_text` 剥 script 的语义影响见 `research.md D4`）。产出探针报告 → 回填 `research.md D4`（09-14 已完成第一遍）。
4. 失败分支：触发 manual_paste 彩排（§5）——**国考线（scs 系不可用）已处于该分支，10/14 前必做彩排**。

## §2 本地全链演练（事件管道）

```bash
cd backend
py -3.13 -m pytest tests/test_source_watch.py tests/test_exam_events.py -q
py -3.13 -m pytest tests/test_announcement_negative.py -q   # §3 负例
```

手工演练：seed 一个本地假源（两样本之一）→ 修改其 content_sha → 跑检测 job → 断言事件行生成且幂等（重跑无新行）→ 事件经 verified 后出现在公开 API。

## §3 负例清单（CI 级，FR7）

| # | 负例 | 期望 |
|---|---|---|
| N1 | 喂 <2KB SPA 壳页 | 拒收，不入 evidence |
| N2 | 喂无证据日期的事件行 | 拒绝过 verified；公开 API 不可见 |
| N3 | 展示文案层：PREDICTED 事件 | 只允许试探式文案（"预计近期"），断言打到最终文案字符串 |
| N4 | manual_paste 文本不含日期串 | 422 拒绝 |
| N5 | 重复 dedup_key 入库 | 幂等忽略 |

## §4 SLA 度量验证

- 造两样本事件（带/不带 published_hint）→ 调 C5 → 断言 `unusable` 计数正确、均值只含有效样本。

## §5 公告日彩排（10/14 D-day 前必做一次）

1. manual_paste 值守通道全链：模拟公告 30 分钟内贴入（用 2026 历史公告原文做演练文本）→ 事件上站 → 考公中心可见。
2. 值守排班表（公告日 08:00–20:00 至少两人窗口覆盖）挂 `docs/` 运行手册。
3. 站内展示冒烟：未登录可见事件流；来源链接可点；可信度标签正确；无空壳引用。

## §6 部署与冒烟（按 house 纪律）

- 发射前 `tools/gp-preflight.sh` 四闸；改完上产（bundle→scp→update_from_bundle.sh）。
- HTTPS 冒烟走 `https://quxianglab.cn`：事件流可见 + 来源可点 + 度量接口 admin-only。
- 冒烟账号验证后删除（house 纪律）。域内探针频率保持低频单页触发；WAF/403 如实记录（不绕过）。
