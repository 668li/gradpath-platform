-- =====================================================================
-- grad_scoreline_records 假数据清理草案（2026-09-01）
-- 状态：草案，未执行。须用户拍板后先在生产预演 SELECT 再 DELETE。
-- 目标：删除 581 条程序合成假记录（伪造来源标签）+ 90 条 0 分占位记录，
--       保留 140 条真实记录（data_sources 含 scorelines_real_data.json）。
-- 预期执行后剩余：140 条。
-- =====================================================================

-- ---- 步骤 0：预演核对（执行 DELETE 前先跑这些 SELECT，行数必须吻合）----
-- 预期 581：
SELECT COUNT(*) FROM grad_scoreline_records
WHERE data_sources::text LIKE '%院校研究生院官网%';
-- 预期 90：
SELECT COUNT(*) FROM grad_scoreline_records
WHERE data_sources::text = '["研招网"]' AND total_score_line = 0;

-- ---- 步骤 1：删除程序合成假记录（伪造"院校研究生院官网/研招网"标签）----
-- 生产实测 581 条；开发库同 581 条。
DELETE FROM grad_scoreline_records
WHERE data_sources::text LIKE '%院校研究生院官网%';

-- ---- 步骤 2：删除 0 分占位记录（"研招网"自申报标签 + total_score_line=0）----
-- 生产实测 90 条；这些是无用占位（决策引擎已有 >0 过滤），随闸门一并清理。
DELETE FROM grad_scoreline_records
WHERE data_sources::text = '["研招网"]' AND total_score_line = 0;

-- ---- 步骤 3：执行后对账（应恰好 140，全部为真实标记）----
SELECT COUNT(*) AS should_be_140 FROM grad_scoreline_records;
SELECT data_sources::text, COUNT(*)
FROM grad_scoreline_records GROUP BY 1;
-- 应只有一行：["scorelines_real_data.json:2026-07-12"] | 140

-- ---- 附注 ----
-- 1. 本清理不碰 GradYanzhaoProgram（招生目录）等其他表。
-- 2. scoreline_real_crawler / scoreline_crawler / admission_ratio_crawler
--    三个伪爬虫仍在注册表：若不处理，重跑会重新灌入合成数据
--    （呈现闸门可挡住用户可见面，但表会被再次污染）。须用户拍板处置方式。
-- 3. SQLite 开发库等价语句：
--    DELETE FROM grad_scoreline_records WHERE data_sources LIKE '%院校研究生院官网%';
--    DELETE FROM grad_scoreline_records WHERE data_sources = '["\u7814\u62db\u7f51"]'
--      AND total_score_line = 0;
--    （注意开发库 JSON 中文以 \uXXXX 转义存储，LIKE 中文匹配不到）
