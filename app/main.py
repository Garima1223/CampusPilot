from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import Base, engine
from app.models import models
from app.routers import (
    auth_router, admin_router, teacher_router, student_router,
    placements_router, notification_router, copilot_router,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CampusPilot API")

# Wide-open CORS for local dev (Vite on :5173/:5174 calling this on :8000).
# Tighten `allow_origins` to your real frontend origin(s) before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(teacher_router.router)
app.include_router(student_router.router)
app.include_router(placements_router.router)
app.include_router(notification_router.router)
app.include_router(copilot_router.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "CampusPilot backend is running"}
