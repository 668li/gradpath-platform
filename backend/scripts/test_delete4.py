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

# Create test log
log = MilestoneLog(
    plan_id=plan.id,
    milestone_index=0,
    content="Test log",
)
db.add(log)
db.commit()
db.refresh(log)

# Test the query directly
log_id_str = str(log.id)
log_uuid = UUID(log_id_str)

print(f"Log ID: {log_id_str}")
print(f"Log UUID: {log_uuid}")

# Test query with UUID
result1 = db.query(MilestoneLog).filter(MilestoneLog.id == log_uuid).first()
print(f"Query with UUID: {result1}")

# Test query with string (no hyphens)
clean_id = log_id_str.replace("-", "")
result2 = db.query(MilestoneLog).filter(MilestoneLog.id == clean_id).first()
print(f"Query with clean string: {result2}")

# Test query with raw SQL
result3 = db.execute(text(f"SELECT * FROM milestone_logs WHERE id = '{log_id_str}'"))
print(f"Query with raw SQL (with hyphens): {list(result3)}")

result4 = db.execute(text(f"SELECT * FROM milestone_logs WHERE id = '{clean_id}'"))
print(f"Query with raw SQL (without hyphens): {list(result4)}")
