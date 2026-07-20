import random, uuid
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    cols = conn.execute(text("SELECT column_name, is_nullable, column_default FROM information_schema.columns WHERE table_name='qas' ORDER BY ordinal_position")).fetchall()
    for c in cols:
        print(c)
