\set ON_ERROR_STOP on
SELECT 'users_left' k, count(*) v FROM users
UNION ALL SELECT 'intel_left', count(*) FROM civil_service_post_intel
UNION ALL SELECT 'smoke_left', count(*) FROM users WHERE email LIKE '%@example.com' OR email = 'integration_test@gradpath.com'
UNION ALL SELECT 'dark_knowledge_kept', count(*) FROM civil_service_dark_knowledge;
