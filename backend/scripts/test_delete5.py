from uuid import UUID, uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.user import User
from app.models.career_plan import CareerPlan
from app.models.milestone_log import MilestoneLog
from app.services.career_plan_service import delete_milestone_log

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

# Test the delete function step by step
log_id_str = str(log.id)
print(f"Log ID: {log_id_str}")

# Step 1: Try to find the log
log_uuid = UUID(log_id_str)
found_log = db.query(MilestoneLog).filter(MilestoneLog.id == log_uuid).first()
print(f"Step 1 - Found log with UUID: {found_log}")

if found_log:
    # Step 2: Try to find the plan
    try:
        plan_uuid = UUID(found_log.plan_id)
        print(f"Step 2 - Plan UUID: {plan_uuid}")
        
        found_plan = db.query(CareerPlan).filter(
            CareerPlan.id == plan_uuid,
            CareerPlan.user_id == user.id
        ).first()
        print(f"Step 2 - Found plan: {found_plan}")
        
        if found_plan:
            # Step 3: Delete the log
            db.delete(found_log)
            db.commit()
            print(f"Step 3 - Deleted log successfully")
            
            # Verify deletion
            remaining = db.query(MilestoneLog).count()
            print(f"Step 3 - Remaining logs: {remaining}")
        else:
            print(f"Step 2 - Plan not found!")
    except Exception as e:
        print(f"Step 2 - Error: {e}")
