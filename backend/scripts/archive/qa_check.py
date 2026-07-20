from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Check qa_answers table columns
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'qa_answers' ORDER BY ordinal_position"))
    print('qa_answers table columns:')
    for row in result:
        print(f'  {row[0]} ({row[1]})')
    print()
    
    # Count qa_answers
    result = conn.execute(text("SELECT COUNT(*) FROM qa_answers"))
    print(f'qa_answers count: {result.scalar()}')
    
    # Count qas without best_answer_id
    result = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NULL"))
    count_no_best = result.scalar()
    print(f'qas without best_answer_id: {count_no_best}')
    
    # Count qas with best_answer_id already set
    result = conn.execute(text("SELECT COUNT(*) FROM qas WHERE best_answer_id IS NOT NULL"))
    count_with_best = result.scalar()
    print(f'qas with best_answer_id: {count_with_best}')
    
    # Check if qa_answers has a foreign key to qas
    result = conn.execute(text("""
        SELECT tc.column_name, kcu.column_name, ccu.table_name AS foreign_table_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'qa_answers'
    """))
    print('\nForeign keys on qa_answers:')
    for row in result:
        print(f'  {row[0]} -> {row[2]}.{row[1]}')
    
    # Sample qa_answers
    result = conn.execute(text("SELECT id, qa_id, content FROM qa_answers LIMIT 3"))
    print('\nSample qa_answers:')
    for row in result:
        print(f'  id={row[0]}, qa_id={row[1]}, content={str(row[2])[:80] if row[2] else None}')
    
    # Sample qas without best_answer_id
    result = conn.execute(text("SELECT id, title FROM qas WHERE best_answer_id IS NULL LIMIT 3"))
    print('\nSample qas without best_answer_id:')
    for row in result:
        print(f'  id={row[0]}, title={row[1][:60] if row[1] else None}')
