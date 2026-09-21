from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import ActivityCreateRequest, PayloadRequest, ReasonRequest, ReviewRequest

router = APIRouter(prefix="/activities", tags=["activities"])
# TODO(Member B): implement M04 review/execution state transitions and registration rules.


@router.post("")
def create_activity(_: CurrentPrincipal, body: ActivityCreateRequest):
    todo("FR-11", "Member B")


@router.get("")
def list_activities(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-14", "Member B")


@router.get("/{activity_id}")
def get_activity(activity_id: int, _: CurrentPrincipal):
    todo("FR-14", "Member B")


@router.patch("/{activity_id}")
def update_activity(activity_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-11", "Member B")


@router.post("/{activity_id}/submit")
def submit_activity(activity_id: int, _: CurrentPrincipal):
    todo("FR-12", "Member B")


@router.post("/{activity_id}/withdraw")
def withdraw_activity(activity_id: int, _: CurrentPrincipal):
    todo("FR-12", "Member B")


@router.post("/{activity_id}/review")
def review_activity(activity_id: int, _: CurrentPrincipal, body: ReviewRequest):
    todo("FR-13", "Member B")


@router.post("/{activity_id}/publish")
def publish_activity(activity_id: int, _: CurrentPrincipal):
    todo("FR-14", "Member B")


@router.post("/{activity_id}/registrations")
def register_activity(activity_id: int, _: CurrentPrincipal):
    todo("FR-15", "Member B")


@router.delete("/{activity_id}/registrations/me")
def cancel_registration(activity_id: int, _: CurrentPrincipal):
    todo("FR-15", "Member B")


@router.get("/{activity_id}/registrations")
def list_registrations(activity_id: int, _: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-15", "Member B")


@router.post("/{activity_id}/cancel")
def cancel_activity(activity_id: int, _: CurrentPrincipal, body: ReasonRequest):
    todo("FR-16", "Member B")


@router.post("/{activity_id}/end")
def end_activity(activity_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-16", "Member B")
