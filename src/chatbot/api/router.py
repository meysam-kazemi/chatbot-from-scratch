from fastapi import APIRouter

from chatbot.api.routes import health


api_router = APIRouter()

api_router.include_router(health.router)