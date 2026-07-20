from sqlalchemy import text
from app.database import engine
with engine.connect() as conn:
    result = conn.execute(text("SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid=t.oid WHERE t.typname='companysize'"))
    for row in result:
        print(row[0])
