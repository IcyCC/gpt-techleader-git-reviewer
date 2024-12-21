from fastapi import APIRouter
from app.api.endpoints import webhook, review

api_router = APIRouter()

api_router.include_router(webhook.router, tags=["webhook"])
api_router.include_router(review.router, prefix="/api", tags=["review"])
