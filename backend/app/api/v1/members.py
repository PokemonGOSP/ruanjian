"""M03 入团/退出、成员申请处理、名册与职务 API。"""

from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.business import ReviewRequest
from app.schemas.common import ApiResponse, PageData
from app.schemas.member import (
    ClubMemberData,
    ClubMemberUpdateRequest,
    MembershipApplicationCreateRequest,
    MembershipApplicationData,
    MembershipProcessResult,
)
from app.services import member_service

router = APIRouter(tags=["members"])

MembershipStatusQuery = Literal["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"]
MembershipTypeQuery = Literal["JOIN", "EXIT"]
MemberStatusQuery = Literal["ACTIVE", "EXITED"]
ScopeQuery = Literal["mine", "managed"]


def _success(data):
    return {"code": 0, "message": "success", "data": data}


@router.post("/membership-applications", response_model=ApiResponse[MembershipApplicationData])
def create_membership_application(
    principal: CurrentPrincipal, db: DbSession, body: MembershipApplicationCreateRequest
):
    return _success(member_service.create_membership_application(db, principal, body))


@router.get(
    "/membership-applications",
    response_model=ApiResponse[PageData[MembershipApplicationData]],
)
def list_membership_applications(
    principal: CurrentPrincipal,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scope: ScopeQuery | None = Query(None),
    club_id: int | None = Query(None, ge=1),
    status: MembershipStatusQuery | None = Query(None),
    application_type: MembershipTypeQuery | None = Query(None),
):
    return _success(
        member_service.list_membership_applications(
            db,
            principal,
            page=page,
            page_size=page_size,
            scope=scope,
            club_id=club_id,
            status=status,
            application_type=application_type,
        )
    )


@router.post(
    "/membership-applications/{application_id}/withdraw",
    response_model=ApiResponse[MembershipApplicationData],
)
def withdraw_membership_application(application_id: int, principal: CurrentPrincipal, db: DbSession):
    return _success(member_service.withdraw_membership_application(db, principal, application_id))


@router.post(
    "/membership-applications/{application_id}/process",
    response_model=ApiResponse[MembershipProcessResult],
)
def process_membership_application(
    application_id: int, principal: CurrentPrincipal, db: DbSession, body: ReviewRequest
):
    return _success(member_service.process_membership_application(db, principal, application_id, body))


@router.get(
    "/clubs/{club_id}/members",
    response_model=ApiResponse[PageData[ClubMemberData]],
)
def list_club_members(
    club_id: int,
    principal: CurrentPrincipal,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: MemberStatusQuery | None = Query(None),
):
    return _success(
        member_service.list_club_members(
            db, principal, club_id, page=page, page_size=page_size, status=status
        )
    )


@router.patch(
    "/clubs/{club_id}/members/{member_id}",
    response_model=ApiResponse[ClubMemberData],
)
def update_club_member(
    club_id: int,
    member_id: int,
    principal: CurrentPrincipal,
    db: DbSession,
    body: ClubMemberUpdateRequest,
):
    return _success(member_service.update_club_member(db, principal, club_id, member_id, body))
