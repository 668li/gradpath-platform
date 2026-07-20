import os
os.environ["LLM_API_KEY"] = ""

from uuid import UUID
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.user import User

# Create test database
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
db = TestingSession()

# Override get_db
def override_get_db():
    try:
        yield db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Register and login
client.post(
    "/api/auth/register",
    json={"email": "test@example.com", "password": "Test1234!", "name": "Test User"},
)
resp = client.post(
    "/api/auth/login",
    json={"email": "test@example.com", "password": "Test1234!"},
)
token = resp.json()["access_token"]
auth_headers = {"Authorization": f"Bearer {token}"}

# Create conversation
conv_resp = client.post(
    "/api/chat/conversations", headers=auth_headers, json={"title": "Test"}
)
print(f"Create conversation: {conv_resp.status_code}")
conv = conv_resp.json()
print(f"Conversation ID: {conv['id']}")

# Send message
resp = client.post(
    f"/api/chat/conversations/{conv['id']}/messages",
    headers=auth_headers,
    json={"content": "Hello"},
)
print(f"Send message status: {resp.status_code}")
print(f"Response: {resp.json()}")
