"""M02 社团注册、社团资料与年审 API。

路径、method 与响应 envelope 沿用 `docs/api/API_CONTRACT_V0_1.md` 和现有
`ApiResponse` / `PageData`；只把 Skeleton 的 PayloadRequest 替换为领域 Schema。
"""

from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.business import ReviewRequest
from app.schemas.club import (
    ClubData,
    ClubRegistrationApplicationData,
    ClubRegistrationCreateRequest,
    ClubRegistrationReviewResult,
    ClubRegistrationUpdateRequest,
    ClubUpdateRequest,
)
from app.schemas.common import ApiResponse, PageData
from app.services import club_service

router = APIRouter(tags=["clubs"])

StatusQuery = Literal["DRAFT", "PENDING", "APPROVED", "REJECTED", "WITHDRAWN"]


def _success(data):
    return {"code": 0, "message": "success", "data": data}


@router.post(
    "/club-registration-applications",
    response_model=ApiResponse[ClubRegistrationApplicationData],
)
def create_registration(
    principal: CurrentPrincipal, db: DbSession, body: ClubRegistrationCreateRequest
):
    return _success(club_service.create_registration_application(db, principal, body))


@router.get(
    "/club-registration-applications",
    response_model=ApiResponse[PageData[ClubRegistrationApplicationData]],
)
def list_registrations(
    principal: CurrentPrincipal,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: StatusQuery | None = Query(None),
):
    return _success(
        club_service.list_registration_applications(
            db, principal, page=page, page_size=page_size, review_status=status
        )
    )


@router.patch(
    "/club-registration-applications/{application_id}",
    response_model=ApiResponse[ClubRegistrationApplicationData],
)
def update_registration(
    application_id: int,
    principal: CurrentPrincipal,
    db: DbSession,
    body: ClubRegistrationUpdateRequest,
):
    return _success(club_service.update_registration_application(db, principal, application_id, body))


@router.post(
    "/club-registration-applications/{application_id}/submit",
    response_model=ApiResponse[ClubRegistrationApplicationData],
)
def submit_registration(application_id: int, principal: CurrentPrincipal, db: DbSession):
    return _success(club_service.submit_registration_application(db, principal, application_id))


@router.post(
    "/club-registration-applications/{application_id}/withdraw",
    response_model=ApiResponse[ClubRegistrationApplicationData],
)
def withdraw_registration(application_id: int, principal: CurrentPrincipal, db: DbSession):
    return _success(club_service.withdraw_registration_application(db, principal, application_id))


@router.post(
    "/club-registration-applications/{application_id}/review",
    response_model=ApiResponse[ClubRegistrationReviewResult],
)
def review_registration(
    application_id: int, principal: CurrentPrincipal, db: DbSession, body: ReviewRequest
):
    return _success(club_service.review_registration_application(db, principal, application_id, body))


@router.get("/clubs", response_model=ApiResponse[PageData[ClubData]])
def list_clubs(
    _: CurrentPrincipal,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return _success(club_service.list_clubs(db, page=page, page_size=page_size))


@router.get("/clubs/{club_id}", response_model=ApiResponse[ClubData])
def get_club(club_id: int, _: CurrentPrincipal, db: DbSession):
    return _success(club_service.get_club(db, club_id))


@router.patch("/clubs/{club_id}", response_model=ApiResponse[ClubData])
def update_club(
    club_id: int, principal: CurrentPrincipal, db: DbSession, body: ClubUpdateRequest
):
    return _success(club_service.update_club(db, principal, club_id, body))
