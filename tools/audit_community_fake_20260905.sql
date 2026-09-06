-- 社区假数据审计 2026-09-05（只读）
\echo === [1] 总量 ===
SELECT 'posts' k, count(*) v FROM posts
UNION ALL SELECT 'experience_posts', count(*) FROM experience_posts
UNION ALL SELECT 'comments', count(*) FROM comments
UNION ALL SELECT 'qas', count(*) FROM qas
UNION ALL SELECT 'qa_answers', count(*) FROM qa_answers
UNION ALL SELECT 'community_ratings', count(*) FROM community_ratings
UNION ALL SELECT 'users_total', count(*) FROM users;

\echo === [2] 嫌疑假用户 ===
SELECT id, email, nickname, username, created_at FROM users
WHERE id::text = '00000000-0000-0000-0000-000000000000'
   OR email LIKE '%gradpath.com' OR email LIKE '%gradpath.local'
ORDER BY created_at LIMIT 60;

\echo === [3] posts 按作者分布 ===
SELECT coalesce(u.email,'<orphan>') email, count(*) FROM posts p LEFT JOIN users u ON u.id=p.user_id GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

\echo === [4] experience_posts 按 platform/status ===
SELECT coalesce(source_platform,'<null>'), status, count(*) FROM experience_posts GROUP BY 1,2 ORDER BY 3 DESC;

\echo === [5] experience_posts 按作者 ===
SELECT coalesce(u.email,'<orphan>') email, count(*) FROM experience_posts p LEFT JOIN users u ON u.id=p.user_id GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

\echo === [6] comments 按作者 ===
SELECT coalesce(u.email,'<orphan>') email, count(*) FROM comments c LEFT JOIN users u ON u.id=c.user_id GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

\echo === [7] comments 挂孤（宿主经验贴不存在）===
SELECT count(*) FROM comments c LEFT JOIN experience_posts p ON p.id=c.post_id WHERE p.id IS NULL;

\echo === [8] qas 按作者 ===
SELECT coalesce(u.email,'<orphan>') email, count(*) FROM qas q LEFT JOIN users u ON u.id=q.user_id GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

\echo === [9] qa_answers 按作者 ===
SELECT coalesce(u.email,'<orphan>') email, count(*) FROM qa_answers a LEFT JOIN users u ON u.id=a.user_id GROUP BY 1 ORDER BY 2 DESC LIMIT 30;

\echo === [10] qa_answers 模板文本 TOP ===
SELECT left(content, 30), count(*) FROM qa_answers GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

\echo === [11] qas 标题模板 TOP ===
SELECT left(title, 30), count(*) FROM qas GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

\echo === [12] posts 内容样本 TOP ===
SELECT left(coalesce(title, content), 30), count(*) FROM posts GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

\echo === [13] 真实用户在社区的发帖（非嫌疑用户）===
SELECT 'posts' k, count(*) FROM posts p JOIN users u ON u.id=p.user_id
 WHERE p.user_id::text <> '00000000-0000-0000-0000-000000000000'
   AND u.email NOT LIKE '%gradpath.com' AND u.email NOT LIKE '%gradpath.local'
UNION ALL SELECT 'experience_posts', count(*) FROM experience_posts p JOIN users u ON u.id=p.user_id
 WHERE coalesce(p.source_platform,'user') = 'user'
   AND p.user_id::text <> '00000000-0000-0000-0000-000000000000'
   AND u.email NOT LIKE '%gradpath.com' AND u.email NOT LIKE '%gradpath.local'
UNION ALL SELECT 'qas', count(*) FROM qas q JOIN users u ON u.id=q.user_id
 WHERE q.user_id::text <> '00000000-0000-0000-0000-000000000000'
   AND u.email NOT LIKE '%gradpath.com' AND u.email NOT LIKE '%gradpath.local'
UNION ALL SELECT 'comments', count(*) FROM comments c JOIN users u ON u.id=c.user_id
 WHERE c.user_id::text <> '00000000-0000-0000-0000-000000000000'
   AND u.email NOT LIKE '%gradpath.com' AND u.email NOT LIKE '%gradpath.local';

\echo === [14] 相邻造假（只报告不删）===
SELECT 'civil_service_post_intel' k, count(*) v FROM civil_service_post_intel
UNION ALL SELECT 'schools', count(*) FROM schools
UNION ALL SELECT 'employment_data', count(*) FROM employment_data
UNION ALL SELECT 'report_records', count(*) FROM report_records;
