-- 阶段 4 A13: pg_trgm GIN 索引补充脚本
-- 用途：为 schools / companies / posts / mentors / skill_nodes 表的 LIKE/ILIKE
-- 搜索字段补充 GIN trgm 索引，加速 '%keyword%' 全文检索。
--
-- 执行方式（已部署环境）：
--   psql -d gradpath -f scripts/add_pg_trgm_indexes.sql
-- 或通过 Alembic 迁移 20260720_add_pgtrgm_gin_indexes_v2.py 自动执行。
--
-- 索引名规范：idx_<table>_<column>_trgm
-- 注：schools.major 字段在模型中不存在（用 key_majors JSONB 存储），故跳过。

-- 启用 pg_trgm 扩展（幂等）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- schools.name
CREATE INDEX IF NOT EXISTS idx_schools_name_trgm
    ON schools USING GIN (name gin_trgm_ops);

-- companies.name
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm
    ON companies USING GIN (name gin_trgm_ops);

-- posts.title / posts.content
CREATE INDEX IF NOT EXISTS idx_posts_title_trgm
    ON posts USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_posts_content_trgm
    ON posts USING GIN (content gin_trgm_ops);

-- mentors.name
CREATE INDEX IF NOT EXISTS idx_mentors_name_trgm
    ON mentors USING GIN (name gin_trgm_ops);

-- skill_nodes.name
CREATE INDEX IF NOT EXISTS idx_skill_nodes_name_trgm
    ON skill_nodes USING GIN (name gin_trgm_ops);

-- 验证：用 EXPLAIN ANALYZE 检查 ILIKE 查询是否走 GIN 索引
-- EXPLAIN ANALYZE SELECT * FROM schools WHERE name ILIKE '%清华%';
-- 应出现 "Bitmap Index Scan on idx_schools_name_trgm"
