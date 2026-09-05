-- 社区纯净度哨兵（2026-09-05 加固配套，建议每周对账一次）
-- 期望：全部 0。任何非 0 行 = 社区表再次被非用户来源污染，按 581 事故流程处置。
SELECT 'experience_posts_non_user' k, count(*) v FROM experience_posts
 WHERE source_platform IS NOT NULL AND source_platform <> 'user'
UNION ALL
SELECT 'posts_by_system', count(*) FROM posts WHERE user_id::text = '00000000-0000-0000-0000-000000000000'
UNION ALL
SELECT 'qa_by_system', count(*) FROM qas WHERE user_id::text = '00000000-0000-0000-0000-000000000000'
UNION ALL
SELECT 'orphan_vectors', count(*) FROM document_embeddings e
 WHERE e.source_table IN ('experience_post','qa')
   AND NOT EXISTS (SELECT 1 FROM experience_posts p WHERE p.id = e.source_id AND e.source_table='experience_post')
   AND NOT EXISTS (SELECT 1 FROM qas q WHERE q.id = e.source_id AND e.source_table='qa');
