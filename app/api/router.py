from fastapi import APIRouter

from app.api import chat, conversations

api_router = APIRouter(prefix="/api")

api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(conversations.router, tags=["conversations"])
