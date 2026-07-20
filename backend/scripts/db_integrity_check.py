"""数据库完整性检查脚本"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "gradpath.db"

def check_tables():
    """检查所有表是否存在"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"数据库表总数: {len(tables)}")
    print("\n表列表:")
    for table in tables:
        print(f"  - {table}")
    
    conn.close()
    return tables

def check_table_schema(table_name):
    """检查表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print(f"\n表 {table_name} 结构:")
    print(f"  字段数: {len(columns)}")
    for col in columns:
        cid, name, col_type, notnull, default, pk = col
        pk_mark = " [PK]" if pk else ""
        notnull_mark = " NOT NULL" if notnull else ""
        print(f"    - {name}: {col_type}{notnull_mark}{pk_mark}")
    
    conn.close()
    return columns

def check_data_counts(tables):
    """检查各表数据量"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n各表数据量:")
    counts = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            counts[table] = count
            print(f"  {table}: {count} 条")
        except Exception as e:
            print(f"  {table}: 查询失败 - {e}")
    
    conn.close()
    return counts

def check_foreign_keys():
    """检查外键关系"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    print("\n外键关系检查:")
    fk_issues = []
    
    for table in tables:
        try:
            cursor.execute(f"PRAGMA foreign_key_list({table});")
            fks = cursor.fetchall()
            
            if fks:
                print(f"\n  表 {table} 的外键:")
                for fk in fks:
                    id, seq, table_ref, from_col, to_col, on_update, on_delete, match = fk
                    print(f"    - {from_col} -> {table_ref}.{to_col}")
                    
                    # 检查外键引用是否有效
                    try:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {table} 
                            WHERE {from_col} IS NOT NULL 
                            AND {from_col} NOT IN (SELECT {to_col} FROM {table_ref});
                        """)
                        invalid_count = cursor.fetchone()[0]
                        if invalid_count > 0:
                            issue = f"表 {table} 的 {from_col} 有 {invalid_count} 条无效外键引用"
                            fk_issues.append(issue)
                            print(f"      ⚠️  {invalid_count} 条无效引用")
                    except Exception as e:
                        print(f"      ⚠️  检查失败: {e}")
        except Exception as e:
            print(f"  表 {table} 外键检查失败: {e}")
    
    conn.close()
    return fk_issues

def check_indexes():
    """检查索引"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, tbl_name FROM sqlite_master 
        WHERE type='index' AND name NOT LIKE 'sqlite_%'
        ORDER BY tbl_name, name;
    """)
    indexes = cursor.fetchall()
    
    print(f"\n索引总数: {len(indexes)}")
    print("\n索引列表:")
    for idx_name, tbl_name in indexes:
        print(f"  - {tbl_name}.{idx_name}")
    
    conn.close()
    return indexes

def main():
    """主检查流程"""
    print("=" * 100)
    print("数据库完整性检查 - GradPath")
    print("=" * 100)
    
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    print(f"\n数据库路径: {DB_PATH}")
    print(f"数据库大小: {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 1. 检查表
    print("\n" + "=" * 100)
    print("【1. 表检查】")
    tables = check_tables()
    
    # 2. 检查关键表结构
    print("\n" + "=" * 100)
    print("【2. 关键表结构检查】")
    key_tables = ['users', 'mentors', 'mentor_reviews', 'experience_posts', 'qas', 'schools']
    for table in key_tables:
        if table in tables:
            check_table_schema(table)
    
    # 3. 检查数据量
    print("\n" + "=" * 100)
    print("【3. 数据量检查】")
    counts = check_data_counts(tables)
    
    # 4. 检查外键
    print("\n" + "=" * 100)
    print("【4. 外键关系检查】")
    fk_issues = check_foreign_keys()
    
    if fk_issues:
        print("\n⚠️  外键问题:")
        for issue in fk_issues:
            print(f"  - {issue}")
    else:
        print("\n✅ 所有外键引用有效")
    
    # 5. 检查索引
    print("\n" + "=" * 100)
    print("【5. 索引检查】")
    indexes = check_indexes()
    
    # 6. 生成报告
    print("\n" + "=" * 100)
    print("数据库完整性检查报告")
    print("=" * 100)
    print(f"表总数: {len(tables)}")
    print(f"索引总数: {len(indexes)}")
    print(f"外键问题数: {len(fk_issues)}")
    
    # 保存报告
    report = {
        "tables": tables,
        "table_count": len(tables),
        "indexes": len(indexes),
        "data_counts": counts,
        "foreign_key_issues": fk_issues
    }
    
    with open('db_integrity_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n详细报告已保存到: db_integrity_report.json")

if __name__ == "__main__":
    main()
