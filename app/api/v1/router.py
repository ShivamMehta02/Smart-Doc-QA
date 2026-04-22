from fastapi import APIRouter
from app.api.v1 import upload, query, chat, status

api_router = APIRouter()

api_router.include_router(upload.router)
api_router.include_router(query.router)
api_router.include_router(chat.router)
api_router.include_router(status.router)
