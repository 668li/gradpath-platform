from uuid import UUID, uuid4
from sqlalchemy import text
from app.database import engine
from app.models.milestone_log import MilestoneLog
from app.models.career_plan import CareerPlan

with engine.connect() as conn:
    # Check milestone_logs
    result = conn.execute(text("SELECT id, plan_id, milestone_index, content FROM milestone_logs LIMIT 5"))
    print("Milestone logs:")
    for row in result:
        print(f"  id={row[0]} (type={type(row[0])}), plan_id={row[1]} (type={type(row[1])})")
    
    # Check career_plans
    result = conn.execute(text("SELECT id, user_id, goal_text FROM career_plans LIMIT 5"))
    print("\nCareer plans:")
    for row in result:
        print(f"  id={row[0]} (type={type(row[0])}), user_id={row[1]} (type={type(row[1])})")
