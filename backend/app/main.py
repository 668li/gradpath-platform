from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.decisions import router as decisions_router
from app.api.events import router as events_router
from app.api.retrospectives import router as retrospectives_router
from app.api.skills import router as skills_router

app = FastAPI(title="GradPath API", version="0.1.0")

app.include_router(auth_router)
app.include_router(decisions_router)
app.include_router(events_router)
app.include_router(skills_router)
app.include_router(retrospectives_router)


@app.get("/health")
def health():
    return {"status": "ok"}
