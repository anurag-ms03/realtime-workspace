from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis
from app.core.config import settings
from app.db.session import engine
from app.api.v1.router import api_router
from app.events import rabbitmq_manager, declare_topology  # ← ADD

app = FastAPI(
    title="Realtime Workspace API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    # ── PostgreSQL ─────────────────────────────────────────────────────────
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ PostgreSQL connected")

    # ── Redis ──────────────────────────────────────────────────────────────
    r = redis.from_url(settings.REDIS_URL)
    r.ping()
    print("✅ Redis connected")

    # ── RabbitMQ ───────────────────────────────────────────────────────────
    await rabbitmq_manager.connect()       # ← ADD
    await declare_topology()               # ← ADD


@app.on_event("shutdown")
async def shutdown_event():                # ← ADD entire handler
    await rabbitmq_manager.disconnect()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "realtime-workspace-api",
        "environment": settings.ENVIRONMENT,
        "rabbitmq": rabbitmq_manager.is_connected,   # ← ADD (nice bonus)
    }