from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis
from app.core.config import settings
from app.db.session import engine
from app.api.v1.router import api_router
from app.events import rabbitmq_manager, declare_topology  # ← ADD
from app.events.consumer_runner import start_consumers, stop_consumers
from app.ws.router import router as ws_router
from app.core.celery_app import celery_app
import httpx

import logging
logging.basicConfig(level=logging.INFO)


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
app.include_router(ws_router)

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

    try:
        await rabbitmq_manager.connect()
        await declare_topology()
        await start_consumers()
        print("✅ RabbitMQ connected")
    except Exception as e:
        print(f"❌ RabbitMQ startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():                # ← ADD entire handler
    await stop_consumers()
    await rabbitmq_manager.disconnect()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "realtime-workspace-api",
        "environment": settings.ENVIRONMENT,
        "rabbitmq": rabbitmq_manager.is_connected,   # ← ADD (nice bonus)
    }
    
    
@app.get("/health/celery")
async def celery_health_check():
    # ── Worker liveness via Celery control API ──────────────────────────────
    inspector = celery_app.control.inspect(timeout=2.0)
    active_workers = inspector.ping() or {}

    worker_status = {
        "workers_online": len(active_workers),
        "worker_names": list(active_workers.keys()),
    }

    # ── Queue depth via RabbitMQ management API ─────────────────────────────
    queue_depth = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "http://localhost:15672/api/queues/%2F/celery",
                auth=("rwuser", "rwpassword"),
                timeout=3.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                queue_depth = {
                    "messages_ready": data.get("messages_ready"),
                    "messages_unacknowledged": data.get("messages_unacknowledged"),
                    "total": data.get("messages"),
                }
    except Exception as e:
        queue_depth = {"error": str(e)}

    return {
        "status": "ok" if worker_status["workers_online"] > 0 else "no_workers",
        "workers": worker_status,
        "queue": queue_depth,
    }