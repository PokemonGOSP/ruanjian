from fastapi import APIRouter

from app.api.v1 import accounts, activities, annual_reviews, auth, clubs, finance, health, members, notifications, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(clubs.router)
api_router.include_router(annual_reviews.router)
api_router.include_router(members.router)
api_router.include_router(activities.router)
api_router.include_router(finance.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
