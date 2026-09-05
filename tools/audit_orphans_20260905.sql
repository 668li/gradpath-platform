-- 多态孤儿引用审计（只读）2026-09-05
\echo === [1] bookmarks 结构 ===
SELECT column_name, data_type, udt_name FROM information_schema.columns WHERE table_name='bookmarks' ORDER BY ordinal_position;
\echo === [2] bookmarks target_type 枚举值分布 ===
SELECT target_type, count(*) FROM bookmarks GROUP BY 1;
\echo === [3] quality_feedback 结构 ===
SELECT column_name, udt_name FROM information_schema.columns WHERE table_name='quality_feedback' ORDER BY ordinal_position;
\echo === [4] quality_feedback target 分布 ===
SELECT target_type, count(*) FROM quality_feedback GROUP BY 1;
\echo === [5] notifications 结构与类型分布 ===
SELECT column_name FROM information_schema.columns WHERE table_name='notifications' ORDER BY ordinal_position;
SELECT type, count(*) FROM notifications GROUP BY 1;
\echo === [6] mentor_reviews 行数 ===
SELECT count(*) FROM mentor_reviews;
\echo === [7] user_memory_facts 行数 ===
SELECT count(*) FROM user_memory_facts;
\echo === [8] reports 行数 ===
SELECT count(*) FROM reports;
