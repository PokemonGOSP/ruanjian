from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import PayloadRequest, ReviewRequest

router = APIRouter(tags=["members"])
# TODO(Member A): implement M03 membership services and club-scoped R02 checks.


@router.post("/membership-applications")
def create_membership_application(_: CurrentPrincipal, body: PayloadRequest):
    todo("FR-08", "Member A")


@router.get("/membership-applications")
def list_membership_applications(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-08/FR-09", "Member A")


@router.post("/membership-applications/{application_id}/withdraw")
def withdraw_membership_application(application_id: int, _: CurrentPrincipal):
    todo("FR-08", "Member A")


@router.post("/membership-applications/{application_id}/process")
def process_membership_application(application_id: int, _: CurrentPrincipal, body: ReviewRequest):
    todo("FR-09", "Member A")


@router.get("/clubs/{club_id}/members")
def list_club_members(club_id: int, _: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-10", "Member A")


@router.patch("/clubs/{club_id}/members/{member_id}")
def update_club_member(club_id: int, member_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-10", "Member A")
