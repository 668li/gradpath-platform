from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='qa_answers' ORDER BY ordinal_position")).fetchall()
    print([c[0] for c in cols])
