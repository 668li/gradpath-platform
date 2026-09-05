-- 社区假数据清除 2026-09-05（用户拍板：社区只能有用户自己发的信息）
-- 审计依据 tools/audit_community_fake_20260905.sql：posts 110 / experience_posts 1847 / qas 75 / qa_answers 155
-- 全部由 system@gradpath.local 以脚本注入（种子/爬虫搬运/模板生成/冒烟残留），真实用户社区内容 = 0
-- 备份：~/backups/community_purge_20260905/（7 表表级 pg_dump）
\set ON_ERROR_STOP on
BEGIN;

DELETE FROM community_ratings;
DELETE FROM comments;
UPDATE qas SET best_answer_id = NULL;
DELETE FROM qa_answers;
DELETE FROM qas;
DELETE FROM posts;
DELETE FROM experience_posts;

-- 孤儿向量清除（派生数据：源行不存在即删，防语义检索复活已删内容）
DELETE FROM document_embeddings WHERE source_table='experience_post' AND NOT EXISTS (SELECT 1 FROM experience_posts p WHERE p.id = source_id);
DELETE FROM document_embeddings WHERE source_table='qa' AND NOT EXISTS (SELECT 1 FROM qas q WHERE q.id = source_id);
DELETE FROM document_embeddings WHERE source_table='scoreline' AND NOT EXISTS (SELECT 1 FROM grad_scoreline_records s WHERE s.id = source_id);
DELETE FROM document_embeddings WHERE source_table='grad_school_intel' AND NOT EXISTS (SELECT 1 FROM grad_school_intel g WHERE g.id = source_id);
DELETE FROM document_embeddings WHERE source_table='salary_benchmark' AND NOT EXISTS (SELECT 1 FROM salary_benchmarks s WHERE s.id = source_id);
DELETE FROM document_embeddings WHERE source_table='dark_knowledge' AND NOT EXISTS (SELECT 1 FROM dark_knowledge d WHERE d.id = source_id);

COMMIT;
