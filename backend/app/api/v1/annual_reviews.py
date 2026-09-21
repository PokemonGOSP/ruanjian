from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import PayloadRequest, ReviewRequest

router = APIRouter(prefix="/annual-reviews", tags=["annual-reviews"])
# TODO(Member A): implement M02 annual review services without automatic club freezing.


@router.post("")
def create_annual_review(_: CurrentPrincipal, body: PayloadRequest):
    todo("FR-06", "Member A")


@router.get("")
def list_annual_reviews(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-06/FR-07", "Member A")


@router.patch("/{application_id}")
def update_annual_review(application_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-06", "Member A")


@router.post("/{application_id}/submit")
def submit_annual_review(application_id: int, _: CurrentPrincipal):
    todo("FR-06", "Member A")


@router.post("/{application_id}/withdraw")
def withdraw_annual_review(application_id: int, _: CurrentPrincipal):
    todo("FR-06", "Member A")


@router.post("/{application_id}/review")
def review_annual_review(application_id: int, _: CurrentPrincipal, body: ReviewRequest):
    todo("FR-07", "Member A")
