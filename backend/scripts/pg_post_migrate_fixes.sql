-- SQLite → PostgreSQL 迁移后的数据面修复（在数据库内部按目录自举执行）。
-- 由 migrate_sqlite_to_pg.py 配套使用，或手工执行：
--   docker exec gradpath-pg psql -U gradpath -d gradpath -f <本文件>
--
-- 包含两个幂等步骤：
--   A. SERIAL 序列对齐：把所有 nextval 驱动的列推进到当前最大值
--   B. varchar 加宽：存量数据超过模型声明长度时按实际最大长度扩列
--      （不截断真实业务数据；每次加宽都会打印 NOTICE 供审计）

DO $$
DECLARE
    r record;
    v_max bigint;
BEGIN
    FOR r IN
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.column_default LIKE 'nextval%'
    LOOP
        EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I',
                       r.column_name, r.table_name) INTO v_max;
        IF v_max > 0 THEN
            PERFORM setval(
                pg_get_serial_sequence(r.table_name, r.column_name),
                v_max);
        END IF;
    END LOOP;
    RAISE NOTICE '[A] SERIAL 序列已全部对齐到 max(id)';
END $$;

DO $$
DECLARE
    r record;
    v_len int;
BEGIN
    FOR r IN
        SELECT c.table_name, c.column_name,
               c.character_maximum_length AS declared
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.data_type = 'character varying'
          AND c.character_maximum_length IS NOT NULL
    LOOP
        EXECUTE format('SELECT MAX(LENGTH(%I)) FROM %I',
                       r.column_name, r.table_name) INTO v_len;
        IF v_len IS NOT NULL AND v_len > r.declared THEN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE varchar(%s)',
                           r.table_name, r.column_name, v_len::text);
            RAISE NOTICE '[B] 加宽 %.% : varchar(%) -> varchar(%)',
                r.table_name, r.column_name, r.declared, v_len;
        END IF;
    END LOOP;
END $$;
