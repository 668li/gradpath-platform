-- 其余用户可见内容表成色盘点（只读，只报告）
SELECT 'mentors' t, count(*) v FROM mentors
UNION ALL SELECT 'knowledge_articles', count(*) FROM knowledge_articles
UNION ALL SELECT 'market_data', count(*) FROM market_data
UNION ALL SELECT 'salary_benchmarks', count(*) FROM salary_benchmarks
UNION ALL SELECT 'companies', count(*) FROM companies
UNION ALL SELECT 'learning_resources', count(*) FROM learning_resources
UNION ALL SELECT 'civil_service_dark_knowledge', count(*) FROM civil_service_dark_knowledge
UNION ALL SELECT 'dark_knowledge(career)', count(*) FROM dark_knowledge
UNION ALL SELECT 'grad_yanzhao_programs', count(*) FROM grad_yanzhao_programs
UNION ALL SELECT 'grad_scoreline_records', count(*) FROM grad_scoreline_records
UNION ALL SELECT 'grad_adjustment_info', count(*) FROM grad_adjustment_info;
