-- 冒烟账号+假考公情报清除 2026-09-05（用户拍板"可"）
-- 审计：7 账号子数据仅 path_comparisons 9 / conversations 3 / user_llm_configs 2（其余 55 表全 0）
-- 备份：~/backups/smoke_intel_purge_20260905/（users/civil_service_post_intel/path_comparisons/conversations/user_llm_configs）
\set ON_ERROR_STOP on
BEGIN;

-- 1. 假考公情报（seed_civil_service.py 手编，唯一来源 run_all_seeds）
DELETE FROM civil_service_post_intel;

-- 2. 冒烟账号子数据（子→父）
DELETE FROM messages
 WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id IN (
  '2d428e80-bd00-4a91-8369-d140bd71dcfe','3633145c-3190-439e-bf2f-a117ac33b04e',
  'fc7d5cca-8391-41fc-abad-875f90a54a93','b2ea4d72-656b-44a7-8c67-e5120148ec55',
  'f86fcd1b-8348-4eb2-bed8-566e0e2b259e','2120c525-9a06-40b0-873a-b7cb7699fa85',
  '81888bad-0ad6-48e8-ae5e-be5f2869b56d'));

DELETE FROM path_comparisons WHERE user_id IN (
  '2d428e80-bd00-4a91-8369-d140bd71dcfe','3633145c-3190-439e-bf2f-a117ac33b04e',
  'fc7d5cca-8391-41fc-abad-875f90a54a93','b2ea4d72-656b-44a7-8c67-e5120148ec55',
  'f86fcd1b-8348-4eb2-bed8-566e0e2b259e','2120c525-9a06-40b0-873a-b7cb7699fa85',
  '81888bad-0ad6-48e8-ae5e-be5f2869b56d');

DELETE FROM user_llm_configs WHERE user_id IN (
  '2d428e80-bd00-4a91-8369-d140bd71dcfe','3633145c-3190-439e-bf2f-a117ac33b04e',
  'fc7d5cca-8391-41fc-abad-875f90a54a93','b2ea4d72-656b-44a7-8c67-e5120148ec55',
  'f86fcd1b-8348-4eb2-bed8-566e0e2b259e','2120c525-9a06-40b0-873a-b7cb7699fa85',
  '81888bad-0ad6-48e8-ae5e-be5f2869b56d');

DELETE FROM conversations WHERE user_id IN (
  '2d428e80-bd00-4a91-8369-d140bd71dcfe','3633145c-3190-439e-bf2f-a117ac33b04e',
  'fc7d5cca-8391-41fc-abad-875f90a54a93','b2ea4d72-656b-44a7-8c67-e5120148ec55',
  'f86fcd1b-8348-4eb2-bed8-566e0e2b259e','2120c525-9a06-40b0-873a-b7cb7699fa85',
  '81888bad-0ad6-48e8-ae5e-be5f2869b56d');

-- 3. 冒烟账号本体（双保险：is_admin=false + email 白名单模式）
DELETE FROM users WHERE id IN (
  '2d428e80-bd00-4a91-8369-d140bd71dcfe','3633145c-3190-439e-bf2f-a117ac33b04e',
  'fc7d5cca-8391-41fc-abad-875f90a54a93','b2ea4d72-656b-44a7-8c67-e5120148ec55',
  'f86fcd1b-8348-4eb2-bed8-566e0e2b259e','2120c525-9a06-40b0-873a-b7cb7699fa85',
  '81888bad-0ad6-48e8-ae5e-be5f2869b56d')
  AND is_admin = false
  AND (email LIKE '%@example.com' OR email = 'integration_test@gradpath.com');

COMMIT;
