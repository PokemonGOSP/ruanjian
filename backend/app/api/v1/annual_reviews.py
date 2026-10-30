"""M02 年审 API（FR-06 / FR-07）。

前缀与路径沿用 Skeleton：`/annual-reviews`。年审驳回只保存状态、意见和通知，
不冻结社团，也不联动限制其他业务。
"""

from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.business import ReviewRequest
from app.schemas.club import (
    AnnualReviewCreateRequest,
    AnnualReviewData,
    AnnualReviewUpdateRequest,
)
from app.schemas.common import ApiResponse, PageData
from app.services import club_service

router = APIRouter(prefix="/annual-reviews", tags=["annual-reviews"])

StatusQuery = Literal["DRAFT", "PENDING", "APPROVED", "REJECTED", "WITHDRAWN"]


def _success(data):
    return {"code": 0, "message": "success", "data": data}


@router.post("", response_model=ApiResponse[AnnualReviewData])
def create_annual_review(
    principal: CurrentPrincipal, db: DbSession, body: AnnualReviewCreateRequest
):
    return _success(club_service.create_annual_review(db, principal, body))


@router.get("", response_model=ApiResponse[PageData[AnnualReviewData]])
def list_annual_reviews(
    principal: CurrentPrincipal,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    club_id: int | None = Query(None, ge=1),
    review_year: int | None = Query(None, ge=2000, le=2100),
    status: StatusQuery | None = Query(None),
):
    return _success(
        club_service.list_annual_reviews(
            db,
            principal,
            page=page,
            page_size=page_size,
            club_id=club_id,
            review_year=review_year,
            review_status=status,
        )
    )


@router.patch("/{application_id}", response_model=ApiResponse[AnnualReviewData])
def update_annual_review(
    application_id: int,
    principal: CurrentPrincipal,
    db: DbSession,
    body: AnnualReviewUpdateRequest,
):
    return _success(club_service.update_annual_review(db, principal, application_id, body))


@router.post("/{application_id}/submit", response_model=ApiResponse[AnnualReviewData])
def submit_annual_review(application_id: int, principal: CurrentPrincipal, db: DbSession):
    return _success(club_service.submit_annual_review(db, principal, application_id))


@router.post("/{application_id}/withdraw", response_model=ApiResponse[AnnualReviewData])
def withdraw_annual_review(application_id: int, principal: CurrentPrincipal, db: DbSession):
    return _success(club_service.withdraw_annual_review(db, principal, application_id))


@router.post("/{application_id}/review", response_model=ApiResponse[AnnualReviewData])
def review_annual_review(
    application_id: int, principal: CurrentPrincipal, db: DbSession, body: ReviewRequest
):
    return _success(club_service.review_annual_review(db, principal, application_id, body))
