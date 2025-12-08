from fastapi import APIRouter

from app.api import chat, conversations, auth, game

api_router = APIRouter(prefix="/api")

api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(auth.router, tags=["auth"], prefix="/auth")
api_router.include_router(game.router, tags=["game"])
