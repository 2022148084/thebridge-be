from fastapi import APIRouter

from app.api.routes import friends, chat, gatherings, items, login, users, utils

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(gatherings.router)
api_router.include_router(friends.router)
api_router.include_router(chat.router)
