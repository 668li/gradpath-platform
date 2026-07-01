from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.community import router as community_router
from app.api.dashboard import router as dashboard_router
from app.api.decisions import router as decisions_router
from app.api.employment import router as employment_router
from app.api.events import router as events_router
from app.api.interview import router as interview_router
from app.api.pipeline import router as pipeline_router
from app.api.posts import router as posts_router
from app.api.retrospectives import router as retrospectives_router
from app.api.skills import router as skills_router
from app.database import Base, engine

# 创建数据库表（开发模式；生产环境使用 Alembic 迁移）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GradPath API", version="0.1.0")

# CORS — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(decisions_router)
app.include_router(events_router)
app.include_router(skills_router)
app.include_router(retrospectives_router)
app.include_router(dashboard_router)
app.include_router(employment_router)
app.include_router(community_router)
app.include_router(interview_router)
app.include_router(pipeline_router)
app.include_router(posts_router)


@app.get("/health")
def health():
    return {"status": "ok"}
