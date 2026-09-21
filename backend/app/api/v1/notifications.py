from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import PayloadRequest

router = APIRouter(prefix="/notifications", tags=["notifications"])
# TODO(Member C): implement M06 in-app notifications only.


@router.get("")
def list_notifications(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-19", "Member C")


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, _: CurrentPrincipal):
    todo("FR-19", "Member C")


@router.post("/read-all")
def mark_all_read(_: CurrentPrincipal):
    todo("FR-19", "Member C")


@router.post("/management")
def publish_management_notification(_: CurrentPrincipal, body: PayloadRequest):
    todo("FR-20", "Member C")
