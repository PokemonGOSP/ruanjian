"""M02 业务服务：社团注册申请、注册审核、社团资料与年审。"""

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import Principal, require_club_leader, require_system_role
from app.db.models.domain import (
    AnnualReviewApplication,
    Club,
    ClubMember,
    ClubRegistrationApplication,
    ClubRoleAssignment,
    MemberStatus,
    ReviewStatus,
)
from app.repositories import club_repository
from app.schemas.business import ReviewRequest
from app.schemas.club import (
    AnnualReviewCreateRequest,
    AnnualReviewUpdateRequest,
    ClubRegistrationCreateRequest,
    ClubRegistrationUpdateRequest,
    ClubUpdateRequest,
    ReviewStatusValue,
)
from app.services import club_member_events


def _now() -> datetime:
    return datetime.now()


def _commit_unique(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(40902, message, 409) from exc


def _status_value(value: ReviewStatus) -> ReviewStatusValue:
    return value.value  # type: ignore[return-value]


def _require_student(principal: Principal) -> None:
    if not principal.has_system_role("R01"):
        raise AppError(40301, "需要 R01 学生用户权限", 403)


def _page(items: list, page: int, page_size: int, total: int) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def registration_data(
    application: ClubRegistrationApplication, applicant_display_name: str | None = None
) -> dict:
    return {
        "id": application.id,
        "applicant_user_id": application.applicant_user_id,
        "applicant_display_name": applicant_display_name,
        "proposed_name": application.proposed_name,
        "description": application.description,
        "advisor_contact": application.advisor_contact,
        "review_status": _status_value(application.review_status),
        "review_comment": application.review_comment,
        "reviewed_by": application.reviewed_by,
        "submitted_at": application.submitted_at,
        "reviewed_at": application.reviewed_at,
        "created_at": application.created_at,
    }


def club_data(club: Club) -> dict:
    return {
        "id": club.id,
        "registration_application_id": club.registration_application_id,
        "name": club.name,
        "description": club.description,
        "advisor_contact": club.advisor_contact,
        "created_at": club.created_at,
        "updated_at": club.updated_at,
    }


def annual_review_data(
    application: AnnualReviewApplication,
    club_name: str | None = None,
    submitter_display_name: str | None = None,
) -> dict:
    return {
        "id": application.id,
        "club_id": application.club_id,
        "club_name": club_name,
        "review_year": application.review_year,
        "submitted_by": application.submitted_by,
        "submitter_display_name": submitter_display_name,
        "materials": application.materials,
        "review_status": _status_value(application.review_status),
        "review_comment": application.review_comment,
        "reviewed_by": application.reviewed_by,
        "submitted_at": application.submitted_at,
        "reviewed_at": application.reviewed_at,
        "created_at": application.created_at,
    }


def create_registration_application(
    db: Session, principal: Principal, body: ClubRegistrationCreateRequest
) -> dict:
    _require_student(principal)
    application = ClubRegistrationApplication(
        applicant_user_id=principal.user_id,
        proposed_name=body.proposed_name,
        description=body.description,
        advisor_contact=body.advisor_contact,
        review_status=ReviewStatus.DRAFT,
    )
    db.add(application)
    db.flush()
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="CLUB_REGISTRATION_CREATE",
        resource_type="club_registration_application",
        resource_id=application.id,
        detail={"proposed_name": application.proposed_name},
    )
    db.commit()
    db.refresh(application)
    return registration_data(application, principal.display_name)


def list_registration_applications(
    db: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    review_status: ReviewStatusValue | None = None,
) -> dict:
    status_enum = ReviewStatus(review_status) if review_status else None
    applicant_filter = None if principal.has_system_role("R03") else principal.user_id
    rows, total = club_repository.list_registration_applications(
        db,
        applicant_user_id=applicant_filter,
        review_status=status_enum,
        page=page,
        page_size=page_size,
    )
    items = [registration_data(application, display_name) for application, display_name in rows]
    return _page(items, page, page_size, total)


def update_registration_application(
    db: Session, principal: Principal, application_id: int, body: ClubRegistrationUpdateRequest
) -> dict:
    application = club_repository.get_registration_application(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "社团注册申请不存在", 404)
    if application.applicant_user_id != principal.user_id:
        raise AppError(40301, "只能修改本人提交的社团注册申请", 403)
    if application.review_status not in {ReviewStatus.DRAFT, ReviewStatus.WITHDRAWN}:
        raise AppError(40901, "只有草稿或已撤回的社团注册申请可以编辑", 409)

    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise AppError(40001, "没有可更新的字段", 422)
    for field, value in payload.items():
        setattr(application, field, value)

    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="CLUB_REGISTRATION_UPDATE",
        resource_type="club_registration_application",
        resource_id=application.id,
        detail={"fields": sorted(payload)},
    )
    db.commit()
    db.refresh(application)
    return registration_data(application, principal.display_name)


def submit_registration_application(db: Session, principal: Principal, application_id: int) -> dict:
    application = club_repository.get_registration_application(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "社团注册申请不存在", 404)
    if application.applicant_user_id != principal.user_id:
        raise AppError(40301, "只能提交本人创建的社团注册申请", 403)
    if application.review_status not in {ReviewStatus.DRAFT, ReviewStatus.WITHDRAWN}:
        raise AppError(40901, "只有草稿或已撤回的社团注册申请可以提交", 409)

    application.review_status = ReviewStatus.PENDING
    application.submitted_at = _now()
    application.review_comment = None
    application.reviewed_by = None
    application.reviewed_at = None
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="CLUB_REGISTRATION_SUBMIT",
        resource_type="club_registration_application",
        resource_id=application.id,
        detail={"proposed_name": application.proposed_name},
    )
    club_member_events.notify_managers(
        db,
        title="新的社团注册申请待审核",
        content=f"社团注册申请“{application.proposed_name}”已提交，请及时审核。",
        event_type="CLUB_REGISTRATION_SUBMITTED",
        related_type="club_registration_application",
        related_id=application.id,
    )
    db.commit()
    db.refresh(application)
    return registration_data(application, principal.display_name)


def withdraw_registration_application(db: Session, principal: Principal, application_id: int) -> dict:
    application = club_repository.get_registration_application(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "社团注册申请不存在", 404)
    if application.applicant_user_id != principal.user_id:
        raise AppError(40301, "只能撤回本人提交的社团注册申请", 403)
    if application.review_status != ReviewStatus.PENDING:
        raise AppError(40901, "只有待审核的社团注册申请可以撤回", 409)

    application.review_status = ReviewStatus.WITHDRAWN
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="CLUB_REGISTRATION_WITHDRAW",
        resource_type="club_registration_application",
        resource_id=application.id,
        detail={"proposed_name": application.proposed_name},
    )
    db.commit()
    db.refresh(application)
    return registration_data(application, principal.display_name)


def review_registration_application(
    db: Session, principal: Principal, application_id: int, body: ReviewRequest
) -> dict:
    require_system_role(principal, "R03")
    application = club_repository.get_registration_application(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "社团注册申请不存在", 404)
    if application.review_status != ReviewStatus.PENDING:
        raise AppError(40901, "只有待审核的社团注册申请可以审核", 409)
    if application.applicant_user_id == principal.user_id:
        raise AppError(40301, "申请人与审核人不得为同一人", 403)

    comment = body.comment.strip() if body.comment else None
    if body.decision == "REJECTED" and not comment:
        raise AppError(40001, "驳回社团注册申请时必须填写理由", 422)

    now = _now()
    application.review_status = ReviewStatus(body.decision)
    application.review_comment = comment
    application.reviewed_by = principal.user_id
    application.reviewed_at = now

    club: Club | None = None
    try:
        if body.decision == "APPROVED":
            if club_repository.get_club_by_registration_application(db, application.id) is not None:
                raise AppError(40902, "该社团注册申请已建立社团", 409)
            if club_repository.get_club_by_name(db, application.proposed_name) is not None:
                raise AppError(40902, "社团名称已存在，无法通过审核", 409)

            club = Club(
                registration_application_id=application.id,
                name=application.proposed_name,
                description=application.description,
                advisor_contact=application.advisor_contact,
            )
            db.add(club)
            db.flush()
            db.add(
                ClubRoleAssignment(
                    user_id=application.applicant_user_id,
                    club_id=club.id,
                    role_code="R02",
                    active=True,
                    granted_by=principal.user_id,
                )
            )
            db.add(
                ClubMember(
                    club_id=club.id,
                    user_id=application.applicant_user_id,
                    position_name="负责人",
                    status=MemberStatus.ACTIVE,
                )
            )
            club_member_events.notify_user(
                db,
                application.applicant_user_id,
                title="社团注册申请已通过",
                content=f"社团注册申请“{application.proposed_name}”已通过审核，已为你授予该社团的 R02 权限。",
                event_type="CLUB_REGISTRATION_APPROVED",
                related_type="club_registration_application",
                related_id=application.id,
            )
        else:
            club_member_events.notify_user(
                db,
                application.applicant_user_id,
                title="社团注册申请已驳回",
                content=(
                    f"社团注册申请“{application.proposed_name}”已驳回。"
                    f"审核意见：{comment or '未填写'}。本次不建立社团，也不授予 R02 权限。"
                ),
                event_type="CLUB_REGISTRATION_REJECTED",
                related_type="club_registration_application",
                related_id=application.id,
            )

        club_member_events.record_audit(
            db,
            actor_user_id=principal.user_id,
            action="CLUB_REGISTRATION_REVIEW",
            resource_type="club_registration_application",
            resource_id=application.id,
            detail={"decision": body.decision, "comment": comment, "club_id": club.id if club else None},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(40902, "社团名称或注册记录存在唯一性冲突", 409) from exc

    db.refresh(application)
    result: dict = {"application": registration_data(application), "club": None, "club_authorization": None}
    if club is not None:
        db.refresh(club)
        result["club"] = club_data(club)
        result["club_authorization"] = {
            "club_id": club.id,
            "user_id": application.applicant_user_id,
            "role_code": "R02",
        }
    return result


def list_clubs(db: Session, *, page: int, page_size: int) -> dict:
    clubs, total = club_repository.list_clubs(db, page=page, page_size=page_size)
    return _page([club_data(club) for club in clubs], page, page_size, total)


def get_club(db: Session, club_id: int) -> dict:
    club = club_repository.get_club(db, club_id)
    if club is None:
        raise AppError(40401, "社团不存在", 404)
    return club_data(club)


def update_club(db: Session, principal: Principal, club_id: int, body: ClubUpdateRequest) -> dict:
    club = club_repository.get_club(db, club_id, for_update=True)
    if club is None:
        raise AppError(40401, "社团不存在", 404)
    require_club_leader(principal, club_id)

    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise AppError(40001, "没有可更新的字段", 422)
    if "name" in payload and payload["name"] != club.name:
        existing = club_repository.get_club_by_name(db, payload["name"])
        if existing is not None and existing.id != club.id:
            raise AppError(40902, "社团名称已存在", 409)
    for field, value in payload.items():
        setattr(club, field, value)

    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="CLUB_PROFILE_UPDATE",
        resource_type="club",
        resource_id=club.id,
        detail={"fields": sorted(payload)},
    )
    _commit_unique(db, "社团名称已存在")
    db.refresh(club)
    return club_data(club)


# ---------------------------------------------------------------------------
# FR-06 / FR-07 年审
# ---------------------------------------------------------------------------


def create_annual_review(db: Session, principal: Principal, body: AnnualReviewCreateRequest) -> dict:
    club = club_repository.get_club(db, body.club_id)
    if club is None:
        raise AppError(40401, "社团不存在", 404)
    require_club_leader(principal, body.club_id)
    if club_repository.get_annual_review_by_club_year(db, body.club_id, body.review_year) is not None:
        raise AppError(40902, "该社团该年度已存在年审申请", 409)

    application = AnnualReviewApplication(
        club_id=body.club_id,
        review_year=body.review_year,
        submitted_by=principal.user_id,
        materials=body.materials,
        review_status=ReviewStatus.DRAFT,
    )
    db.add(application)
    db.flush()
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="ANNUAL_REVIEW_CREATE",
        resource_type="annual_review_application",
        resource_id=application.id,
        detail={"club_id": body.club_id, "review_year": body.review_year},
    )
    _commit_unique(db, "该社团该年度已存在年审申请")
    db.refresh(application)
    return annual_review_data(application, club.name, principal.display_name)


def list_annual_reviews(
    db: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    club_id: int | None = None,
    review_year: int | None = None,
    review_status: ReviewStatusValue | None = None,
) -> dict:
    if club_id is not None:
        club = club_repository.get_club(db, club_id)
        if club is None:
            raise AppError(40401, "社团不存在", 404)
        if not principal.has_system_role("R03"):
            require_club_leader(principal, club_id)
        club_ids: list[int] | None = [club_id]
    elif principal.has_system_role("R03"):
        club_ids = None
    elif principal.club_leader_ids:
        club_ids = sorted(principal.club_leader_ids)
    else:
        raise AppError(40301, "需要 R03 或目标社团 R02 权限", 403)

    status_enum = ReviewStatus(review_status) if review_status else None
    rows, total = club_repository.list_annual_reviews(
        db,
        club_ids=club_ids,
        review_status=status_enum,
        review_year=review_year,
        page=page,
        page_size=page_size,
    )
    items = [
        annual_review_data(application, club_name, submitter_name)
        for application, club_name, submitter_name in rows
    ]
    return _page(items, page, page_size, total)


def update_annual_review(
    db: Session, principal: Principal, application_id: int, body: AnnualReviewUpdateRequest
) -> dict:
    application = club_repository.get_annual_review(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "年审申请不存在", 404)
    require_club_leader(principal, application.club_id)
    if application.review_status not in {ReviewStatus.DRAFT, ReviewStatus.WITHDRAWN}:
        raise AppError(40901, "只有草稿或已撤回的年审申请可以编辑", 409)

    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise AppError(40001, "没有可更新的字段", 422)
    if "review_year" in payload and payload["review_year"] != application.review_year:
        existing = club_repository.get_annual_review_by_club_year(
            db, application.club_id, payload["review_year"]
        )
        if existing is not None and existing.id != application.id:
            raise AppError(40902, "该社团该年度已存在年审申请", 409)
    for field, value in payload.items():
        setattr(application, field, value)

    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="ANNUAL_REVIEW_UPDATE",
        resource_type="annual_review_application",
        resource_id=application.id,
        detail={"fields": sorted(payload)},
    )
    _commit_unique(db, "该社团该年度已存在年审申请")
    db.refresh(application)
    club = club_repository.get_club(db, application.club_id)
    return annual_review_data(application, club.name if club else None)


def submit_annual_review(db: Session, principal: Principal, application_id: int) -> dict:
    application = club_repository.get_annual_review(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "年审申请不存在", 404)
    require_club_leader(principal, application.club_id)
    if application.review_status not in {ReviewStatus.DRAFT, ReviewStatus.WITHDRAWN}:
        raise AppError(40901, "只有草稿或已撤回的年审申请可以提交", 409)

    application.review_status = ReviewStatus.PENDING
    application.submitted_by = principal.user_id
    application.submitted_at = _now()
    application.review_comment = None
    application.reviewed_by = None
    application.reviewed_at = None
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="ANNUAL_REVIEW_SUBMIT",
        resource_type="annual_review_application",
        resource_id=application.id,
        detail={"club_id": application.club_id, "review_year": application.review_year},
    )
    club = club_repository.get_club(db, application.club_id)
    club_name = club.name if club else str(application.club_id)
    club_member_events.notify_managers(
        db,
        title="新的年审申请待审核",
        content=f"社团“{club_name}”的 {application.review_year} 年度年审申请已提交。",
        event_type="ANNUAL_REVIEW_SUBMITTED",
        related_type="annual_review_application",
        related_id=application.id,
    )
    db.commit()
    db.refresh(application)
    return annual_review_data(application, club.name if club else None, principal.display_name)


def withdraw_annual_review(db: Session, principal: Principal, application_id: int) -> dict:
    application = club_repository.get_annual_review(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "年审申请不存在", 404)
    require_club_leader(principal, application.club_id)
    if application.review_status != ReviewStatus.PENDING:
        raise AppError(40901, "只有待审核的年审申请可以撤回", 409)

    application.review_status = ReviewStatus.WITHDRAWN
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="ANNUAL_REVIEW_WITHDRAW",
        resource_type="annual_review_application",
        resource_id=application.id,
        detail={"club_id": application.club_id, "review_year": application.review_year},
    )
    db.commit()
    db.refresh(application)
    club = club_repository.get_club(db, application.club_id)
    return annual_review_data(application, club.name if club else None)


def review_annual_review(
    db: Session, principal: Principal, application_id: int, body: ReviewRequest
) -> dict:
    require_system_role(principal, "R03")
    application = club_repository.get_annual_review(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "年审申请不存在", 404)
    if application.review_status != ReviewStatus.PENDING:
        raise AppError(40901, "只有待审核的年审申请可以审核", 409)
    if application.submitted_by == principal.user_id:
        raise AppError(40301, "申请人与审核人不得为同一人", 403)

    comment = body.comment.strip() if body.comment else None
    if body.decision == "REJECTED" and not comment:
        raise AppError(40001, "驳回年审申请时必须填写意见", 422)

    application.review_status = ReviewStatus(body.decision)
    application.review_comment = comment
    application.reviewed_by = principal.user_id
    application.reviewed_at = _now()
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="ANNUAL_REVIEW_REVIEW",
        resource_type="annual_review_application",
        resource_id=application.id,
        detail={
            "decision": body.decision,
            "comment": comment,
            "club_id": application.club_id,
            "review_year": application.review_year,
        },
    )
    club_member_events.notify_user(
        db,
        application.submitted_by,
        title="年审审核结果",
        content=(
            f"你提交的 {application.review_year} 年度年审申请已"
            f"{'通过' if body.decision == 'APPROVED' else '驳回'}。"
            f"审核意见：{comment or '无'}。"
        ),
        event_type=f"ANNUAL_REVIEW_{body.decision}",
        related_type="annual_review_application",
        related_id=application.id,
    )
    db.commit()
    db.refresh(application)
    club = club_repository.get_club(db, application.club_id)
    return annual_review_data(application, club.name if club else None)
