from uuid import UUID, uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.user import User
from app.models.career_plan import CareerPlan
from app.models.milestone_log import MilestoneLog

# Create test database
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
db = TestingSession()

# Create test user
user = User(email="test@example.com", name="Test User", password_hash="hashed")
db.add(user)
db.commit()
db.refresh(user)

# Create test plan
plan = CareerPlan(
    user_id=user.id,
    goal_text="Test goal",
    current_state={},
    target_state={},
    gaps=[],
    milestones=[{"title": "Milestone 1", "description": "Test", "status": "pending"}],
    timeline_months=6,
    status="draft",
)
db.add(plan)
db.commit()
db.refresh(plan)

print(f"Plan ID: {plan.id} (type: {type(plan.id)})")

# Create test log
log = MilestoneLog(
    plan_id=plan.id,
    milestone_index=0,
    content="Test log",
)
db.add(log)
db.commit()
db.refresh(log)

print(f"Log ID: {log.id} (type: {type(log.id)})")
print(f"Log plan_id: {log.plan_id} (type: {type(log.plan_id)})")

# Check if log exists in database
result = db.execute(text("SELECT id, plan_id FROM milestone_logs"))
print("\nLogs in database:")
for row in result:
    print(f"  id={row[0]} (type: {type(row[0])}), plan_id={row[1]} (type: {type(row[1])})")

# Test delete
from app.services.career_plan_service import delete_milestone_log
log_id_str = str(log.id)
print(f"\nTrying to delete log with id: {log_id_str}")
result = delete_milestone_log(db, user.id, log_id_str)
print(f"Delete result: {result}")
print(f"Delete result type: {type(result)}")

# Check if log still exists
result = db.execute(text("SELECT id FROM milestone_logs"))
print(f"\nLogs after delete: {len(list(result))}")
