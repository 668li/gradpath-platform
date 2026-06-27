from fastapi import FastAPI

from app.api.auth import router as auth_router

app = FastAPI(title="GradPath API", version="0.1.0")

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}
