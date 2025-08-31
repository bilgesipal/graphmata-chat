from fastapi import APIRouter
from src.routers import chat_router, health_router

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(chat_router.router)
api_router.include_router(health_router.router)


