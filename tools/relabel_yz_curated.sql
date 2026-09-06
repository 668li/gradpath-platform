-- 信任锚书 T3：grad_yanzhao_programs 150 行标签诚实化（2026-09-06）
-- 背景：数据是「公开招生简章人工整理」（真内容），但原标签
--       ["研招网专业目录"] 借假爬虫管道入库（管道已 R3 根除）——
--       洗为 curated 显式策展标签，与「非爬取」事实一致。
-- 执行时机：代码部署后，生产 psql --single-transaction -v ON_ERROR_STOP=1 -f

BEGIN;

-- 预检（应 =150）
SELECT 'precheck_should_be_150' AS chk, count(*) FROM grad_yanzhao_programs
WHERE data_sources = '["研招网专业目录"]'::jsonb;

UPDATE grad_yanzhao_programs
SET data_sources = '["curated:2026年招生简章（公开渠道整理，非爬取）"]'::jsonb
WHERE data_sources = '["研招网专业目录"]'::jsonb;

-- 复核（curated=150，旧标签=0，行数不变=150）
SELECT 'curated_labeled' AS chk, count(*) FROM grad_yanzhao_programs
WHERE data_sources = '["curated:2026年招生简章（公开渠道整理，非爬取）"]'::jsonb
UNION ALL
SELECT 'old_label_left', count(*) FROM grad_yanzhao_programs
WHERE data_sources = '["研招网专业目录"]'::jsonb
UNION ALL
SELECT 'total_rows_unchanged', count(*) FROM grad_yanzhao_programs;

COMMIT;
