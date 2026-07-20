# 外部调研能力映射规则

本文档定义 GradPath 外部调研模块抓取到的不同来源内容如何映射到现有数据模型。

## 映射总览

| 来源类型 | 目标模型 | 说明 |
|---|---|---|
| B站视频 | `ExperiencePost` | 将视频标题/简介/评论区精华整理为经验贴，保留原视频链接 |
| 网页文章 | `ExperiencePost` / `DarkKnowledge` | 经验类、个人复盘映射为经验贴；流程性、规则性知识映射为暗知识 |
| RSS 源 | `KaoyanNews` / `GradAdjustmentInfo` | 政策/招生简章/复试资讯进入资讯表；调剂类信息可抽取为调剂情报 |

## 详细规则

### B站视频 → ExperiencePost

- `title`：视频标题（可稍加清洗，去掉 UP 主口播语气词）。
- `summary`：视频简介或 AI 生成的内容摘要，不超过 500 字。
- `content`：评论区高赞经验 + 视频字幕/文稿的整理正文。
- `source_platform`：`"bilibili"`。
- `source_url`：B站视频原链接。
- `external_view_count`：视频播放量。
- `external_like_count`：视频点赞数。
- `category`：根据内容映射到 `general/初试/复试/调剂/择校/复习`。
- `tags`：提取视频标签、关键词、院校/专业等。
- `status`：默认 `"pending"`，审核后展示。

### 网页文章 → ExperiencePost / DarkKnowledge

#### 经验贴类文章（个人备考复盘、上岸分享）

映射到 `ExperiencePost`，规则与 B站视频类似：

- `source_platform`：文章所在平台，如 `"zhihu"`、`"xiaohongshu"`、`"forum"`。
- `source_url`：原文链接。
- `external_view_count` / `external_like_count`：文章阅读量/点赞量（若可获取）。

#### 知识/规则类文章（政策解读、流程说明、避坑指南）

映射到 `DarkKnowledge`：

- `title`：文章核心知识点标题。
- `content`：整理后的结构化内容。
- `stage`：`decision / school_selection / preparation / exam / retest / transfer`。
- `category`：知识分类，如 `"政策"`、`"调剂规则"`、`"复试流程"`。
- `actionable_advice`：可执行建议。
- `verification_method`：建议的验证方法/官方链接。

### RSS → KaoyanNews / GradAdjustmentInfo

#### 通用资讯

映射到 `KaoyanNews`：

- `title` / `summary` / `content`：RSS 标题、摘要、正文。
- `source_platform`：`"rss"`（或具体 RSS 源名称）。
- `source_url`：原文唯一链接（用于去重）。
- `published_at`：RSS 中的发布时间。
- `category`：根据关键词映射为 `政策 / 调剂 / 招生简章 / 复试 / general`。
- `tags`：自动提取的标签列表。
- `status`：默认 `"pending"`，人工/自动审核后改为 `"approved"`。

#### 调剂信息

对于包含明确调剂名额、生源要求、联系方式的 RSS 条目，可进一步映射到 `GradAdjustmentInfo`：

- `university_name` / `department` / `major_name`：从标题/正文中抽取。
- `adjustment_quota` / `original_major_range` / `deadline` / `contact_email` / `contact_phone`：结构化抽取。
- `source_url`：原文链接。
- `year`：招生年份，默认当年。
- `status`：`"open"`。

## 状态流转

1. 爬虫/RSS 抓取后先写入目标模型，状态为 `"pending"`。
2. 自动规则/人工审核后改为 `"approved"` 或 `"rejected"`。
3. `ExperiencePost` 与 `KaoyanNews` 的本地统计（`view_count`、`like_count`）与外部统计（`external_*`）独立存储，便于后续比对数据来源质量。
