-- 孤儿 quality_feedback 清除 2026-09-05（对抗审查 A：指向已删经验贴的反馈）
-- 备份：~/backups/smoke_intel_purge_20260905/quality_feedback.sql
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM quality_feedback
 WHERE target_type = 'experience_post'
   AND NOT EXISTS (SELECT 1 FROM experience_posts p WHERE p.id::text = target_id);
COMMIT;
