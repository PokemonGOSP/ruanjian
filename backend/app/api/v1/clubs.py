from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import PayloadRequest, ReviewRequest

router = APIRouter(tags=["clubs"])
# TODO(Member A): implement M02 club registration and profile services from the stable contract.


@router.post("/club-registration-applications")
def create_registration(_: CurrentPrincipal, body: PayloadRequest):
    todo("FR-03", "Member A")


@router.get("/club-registration-applications")
def list_registrations(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-03/FR-05", "Member A")


@router.patch("/club-registration-applications/{application_id}")
def update_registration(application_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-03", "Member A")


@router.post("/club-registration-applications/{application_id}/submit")
def submit_registration(application_id: int, _: CurrentPrincipal):
    todo("FR-03", "Member A")


@router.post("/club-registration-applications/{application_id}/withdraw")
def withdraw_registration(application_id: int, _: CurrentPrincipal):
    todo("FR-03", "Member A")


@router.post("/club-registration-applications/{application_id}/review")
def review_registration(application_id: int, _: CurrentPrincipal, body: ReviewRequest):
    todo("FR-05", "Member A")


@router.get("/clubs")
def list_clubs(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-04", "Member A")


@router.get("/clubs/{club_id}")
def get_club(club_id: int, _: CurrentPrincipal):
    todo("FR-04", "Member A")


@router.patch("/clubs/{club_id}")
def update_club(club_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-04", "Member A")
