from fastapi import APIRouter
from app.api.v1 import auth
from app.api.v1.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])