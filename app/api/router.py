from fastapi import APIRouter

from app.api import admin, chat, conversations, auth, game, notifications

api_router = APIRouter(prefix="/api")

api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(auth.router, tags=["auth"], prefix="/auth")
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(game.router, tags=["game"])
api_router.include_router(notifications.router, tags=["notifications"])
