from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: DbSession) -> dict:
    database = "up"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database = "down"
    service = "up" if database == "up" else "degraded"
    return {"code": 0, "message": "success", "data": {"service": service, "database": database}}
