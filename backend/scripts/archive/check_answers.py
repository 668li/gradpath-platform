from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Check if answers table has data
    result = conn.execute(text("SELECT COUNT(*) FROM answers"))
    print(f'answers table count: {result.scalar()}')
    
    # Check qa_answers table if it exists
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM qa_answers"))
        print(f'qa_answers table count: {result.scalar()}')
        result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'qa_answers' ORDER BY ordinal_position"))
        print('qa_answers columns:')
        for row in result:
            print(f'  {row[0]} ({row[1]})')
    except:
        print('qa_answers table does not exist')
    
    # Check all tables
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
    print('\nAll public tables:')
    for row in result:
        print(f'  {row[0]}')
    
    # Sample qas
    result = conn.execute(text("SELECT id, title, best_answer_id FROM qas WHERE best_answer_id IS NULL LIMIT 5"))
    print('\nSample qas without best_answer_id:')
    for row in result:
        print(f'  id={row[0]}, title={row[1][:50] if row[1] else None}, best_answer_id={row[2]}')
