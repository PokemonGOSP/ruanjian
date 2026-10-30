"""M03 业务服务：入团/退出申请、成员申请处理、名册与社团职务。"""

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import Principal, require_club_leader
from app.db.models.domain import (
    ClubMember,
    MembershipApplication,
    MembershipApplicationStatus,
    MembershipType,
    MemberStatus,
)
from app.repositories import club_repository, member_repository
from app.schemas.business import ReviewRequest
from app.schemas.member import (
    ClubMemberUpdateRequest,
    MembershipApplicationCreateRequest,
)
from app.services import club_member_events


def _now() -> datetime:
    return datetime.now()


def _require_student(principal: Principal) -> None:
    if not principal.has_system_role("R01"):
        raise AppError(40301, "需要 R01 学生用户权限", 403)


def _page(items: list, page: int, page_size: int, total: int) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def membership_data(
    application: MembershipApplication,
    *,
    club_name: str | None = None,
    applicant_display_name: str | None = None,
    processor_display_name: str | None = None,
) -> dict:
    return {
        "id": application.id,
        "club_id": application.club_id,
        "club_name": club_name,
        "applicant_user_id": application.applicant_user_id,
        "applicant_display_name": applicant_display_name,
        "application_type": application.application_type.value,
        "reason": application.reason,
        "status": application.status.value,
        "processed_by": application.processed_by,
        "processed_by_display_name": processor_display_name,
        "process_comment": application.process_comment,
        "created_at": application.created_at,
        "processed_at": application.processed_at,
    }


def member_data(
    member: ClubMember,
    *,
    username: str | None = None,
    display_name: str | None = None,
    limited: bool = False,
) -> dict:
    data = {
        "id": member.id,
        "club_id": member.club_id,
        "display_name": display_name or username or f"用户{member.user_id}",
        "position_name": member.position_name,
        "status": member.status.value,
        "user_id": None if limited else member.user_id,
        "username": None if limited else username,
        "joined_at": None if limited else member.joined_at,
        "exited_at": None if limited else member.exited_at,
    }
    return data


def create_membership_application(
    db: Session, principal: Principal, body: MembershipApplicationCreateRequest
) -> dict:
    _require_student(principal)
    club = club_repository.get_club(db, body.club_id)
    if club is None:
        raise AppError(40002, "目标社团不存在", 400)

    membership = member_repository.get_membership(db, body.club_id, principal.user_id)
    pending = member_repository.get_pending_application(db, body.club_id, principal.user_id)
    if pending is not None:
        raise AppError(40902, "该社团已存在待处理的成员申请", 409)

    if body.application_type == "JOIN":
        if membership is not None and membership.status == MemberStatus.ACTIVE:
            raise AppError(40002, "你已是该社团的有效成员，不能重复入团", 400)
    else:
        if membership is None or membership.status != MemberStatus.ACTIVE:
            raise AppError(40002, "只有该社团的有效成员可以申请退出", 400)

    application = MembershipApplication(
        club_id=body.club_id,
        applicant_user_id=principal.user_id,
        application_type=MembershipType(body.application_type),
        reason=body.reason,
        status=MembershipApplicationStatus.PENDING,
    )
    db.add(application)
    db.flush()
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action=f"MEMBERSHIP_{body.application_type}_APPLY",
        resource_type="membership_application",
        resource_id=application.id,
        detail={"club_id": body.club_id, "application_type": body.application_type},
    )
    club_member_events.notify_club_leaders(
        db,
        body.club_id,
        title="新的成员申请待处理",
        content=f"{principal.display_name} 提交了{'入团' if body.application_type == 'JOIN' else '退出'}申请。",
        event_type="MEMBERSHIP_APPLICATION_SUBMITTED",
        related_type="membership_application",
        related_id=application.id,
    )
    db.commit()
    db.refresh(application)
    return membership_data(application, club_name=club.name, applicant_display_name=principal.display_name)


def list_membership_applications(
    db: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    scope: str | None = None,
    club_id: int | None = None,
    status: str | None = None,
    application_type: str | None = None,
) -> dict:
    if scope not in {None, "mine", "managed"}:
        raise AppError(40001, "scope 只能是 mine 或 managed", 422)

    led_clubs = sorted(principal.club_leader_ids)
    applicant_filter: int | None = None
    club_filter: list[int] | None = None
    combine_or = False

    if scope == "mine":
        applicant_filter = principal.user_id
    elif scope == "managed":
        if not led_clubs:
            raise AppError(40301, "需要目标社团 R02 权限", 403)
        if club_id is not None:
            if club_id not in principal.club_leader_ids:
                raise AppError(40302, "没有该社团的 R02 权限", 403)
            club_filter = [club_id]
        else:
            club_filter = led_clubs
    else:
        if club_id is not None:
            if club_id in principal.club_leader_ids:
                club_filter = [club_id]
            else:
                applicant_filter = principal.user_id
        elif led_clubs:
            applicant_filter = principal.user_id
            club_filter = led_clubs
            combine_or = True
        else:
            applicant_filter = principal.user_id

    status_enum = MembershipApplicationStatus(status) if status else None
    type_enum = MembershipType(application_type) if application_type else None
    rows, total = member_repository.list_membership_applications(
        db,
        applicant_user_id=applicant_filter,
        club_ids=club_filter,
        combine_or=combine_or,
        club_id=club_id,
        status=status_enum,
        application_type=type_enum,
        page=page,
        page_size=page_size,
    )
    items = [
        membership_data(
            application,
            club_name=club_name,
            applicant_display_name=applicant_name,
            processor_display_name=processor_name,
        )
        for application, club_name, applicant_name, processor_name in rows
    ]
    return _page(items, page, page_size, total)


def withdraw_membership_application(db: Session, principal: Principal, application_id: int) -> dict:
    application = member_repository.get_membership_application(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "成员申请不存在", 404)
    if application.applicant_user_id != principal.user_id:
        raise AppError(40301, "只能撤回本人的成员申请", 403)
    if application.status != MembershipApplicationStatus.PENDING:
        raise AppError(40901, "只有待处理的成员申请可以撤回", 409)

    application.status = MembershipApplicationStatus.WITHDRAWN
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="MEMBERSHIP_APPLICATION_WITHDRAW",
        resource_type="membership_application",
        resource_id=application.id,
        detail={"club_id": application.club_id, "application_type": application.application_type.value},
    )
    db.commit()
    db.refresh(application)
    club = club_repository.get_club(db, application.club_id)
    return membership_data(
        application,
        club_name=club.name if club else None,
        applicant_display_name=principal.display_name,
    )


def process_membership_application(
    db: Session, principal: Principal, application_id: int, body: ReviewRequest
) -> dict:
    application = member_repository.get_membership_application(db, application_id, for_update=True)
    if application is None:
        raise AppError(40401, "成员申请不存在", 404)
    require_club_leader(principal, application.club_id)
    if application.status != MembershipApplicationStatus.PENDING:
        raise AppError(40901, "只有待处理的成员申请可以处理", 409)
    if application.applicant_user_id == principal.user_id:
        raise AppError(40301, "申请人与处理人不得为同一人", 403)

    comment = body.comment.strip() if body.comment else None
    applicant = member_repository.get_user(db, application.applicant_user_id)
    applicant_name = applicant.display_name if applicant else None
    member: ClubMember | None = None

    try:
        if body.decision == "APPROVED":
            member = member_repository.get_membership(
                db, application.club_id, application.applicant_user_id, for_update=True
            )
            if application.application_type == MembershipType.JOIN:
                if member is not None and member.status == MemberStatus.ACTIVE:
                    raise AppError(40901, "申请人已是该社团有效成员", 409)
                if member is None:
                    member = ClubMember(
                        club_id=application.club_id,
                        user_id=application.applicant_user_id,
                        position_name=None,
                        status=MemberStatus.ACTIVE,
                        joined_at=_now(),
                    )
                    db.add(member)
                else:
                    member.status = MemberStatus.ACTIVE
                    member.joined_at = _now()
                    member.exited_at = None
                    member.position_name = None
            else:
                if member is None or member.status != MemberStatus.ACTIVE:
                    raise AppError(40901, "申请人不是该社团有效成员，无法退出", 409)
                member.status = MemberStatus.EXITED
                member.exited_at = _now()

        application.status = MembershipApplicationStatus(body.decision)
        application.processed_by = principal.user_id
        application.processed_at = _now()
        application.process_comment = comment

        club_member_events.record_audit(
            db,
            actor_user_id=principal.user_id,
            action="MEMBERSHIP_APPLICATION_PROCESS",
            resource_type="membership_application",
            resource_id=application.id,
            detail={
                "decision": body.decision,
                "comment": comment,
                "club_id": application.club_id,
                "application_type": application.application_type.value,
            },
        )
        club_member_events.notify_user(
            db,
            application.applicant_user_id,
            title="成员申请处理结果",
            content=(
                f"你提交的{'入团' if application.application_type == MembershipType.JOIN else '退出'}申请已"
                f"{'同意' if body.decision == 'APPROVED' else '驳回'}。"
                f"处理意见：{comment or '无'}。"
            ),
            event_type=f"MEMBERSHIP_APPLICATION_{body.decision}",
            related_type="membership_application",
            related_id=application.id,
        )
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(40902, "成员关系或申请记录存在唯一性冲突", 409) from exc

    db.refresh(application)
    if member is not None:
        db.refresh(member)
    club = club_repository.get_club(db, application.club_id)
    result = {
        "application": membership_data(
            application,
            club_name=club.name if club else None,
            applicant_display_name=applicant_name,
            processor_display_name=principal.display_name,
        ),
        "member": None,
    }
    if member is not None:
        result["member"] = member_data(
            member, username=applicant.username if applicant else None, display_name=applicant_name
        )
    return result


def list_club_members(
    db: Session,
    principal: Principal,
    club_id: int,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
) -> dict:
    club = club_repository.get_club(db, club_id)
    if club is None:
        raise AppError(40401, "社团不存在", 404)

    full_access = principal.leads_club(club_id)
    if not full_access:
        own_membership = member_repository.get_membership(db, club_id, principal.user_id)
        if own_membership is None or own_membership.status != MemberStatus.ACTIVE:
            raise AppError(40302, "只有本社团负责人或有效成员可以查看名册", 403)

    status_enum = MemberStatus(status) if status else None
    member_filter: int | None = None
    if not full_access:
        # FR-10：成员查看与本人相关的信息；受限视图只返回本人有效记录。
        status_enum = MemberStatus.ACTIVE
        member_filter = principal.user_id
    rows, total = member_repository.list_club_members(
        db,
        club_id=club_id,
        user_id=member_filter,
        status=status_enum,
        page=page,
        page_size=page_size,
    )
    items = [
        member_data(member, username=username, display_name=display_name, limited=not full_access)
        for member, username, display_name in rows
    ]
    return _page(items, page, page_size, total)


def update_club_member(
    db: Session, principal: Principal, club_id: int, member_id: int, body: ClubMemberUpdateRequest
) -> dict:
    member = member_repository.get_member(db, club_id, member_id, for_update=True)
    if member is None:
        raise AppError(40401, "成员不存在", 404)
    require_club_leader(principal, club_id)
    if member.status != MemberStatus.ACTIVE:
        raise AppError(40901, "只有有效成员可以维护社团职务", 409)

    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise AppError(40001, "没有可更新的字段", 422)
    member.position_name = payload.get("position_name")
    club_member_events.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="CLUB_MEMBER_POSITION_UPDATE",
        resource_type="club_member",
        resource_id=member.id,
        detail={"club_id": club_id, "position_name": member.position_name},
    )
    db.commit()
    db.refresh(member)
    user = member_repository.get_user(db, member.user_id)
    return member_data(
        member,
        username=user.username if user else None,
        display_name=user.display_name if user else None,
    )
