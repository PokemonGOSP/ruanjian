import json
from collections import defaultdict

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentPrincipal, DbSession
from app.api.v1.skeleton import todo
from app.core.exceptions import AppError
from app.core.permissions import require_system_role
from app.core.security import hash_password
from app.db.models.domain import AccountStatus, AuditLog, Club, ClubRoleAssignment, SystemRoleAssignment, User
from app.schemas.business import (
    AccountCreateRequest,
    AccountData,
    AccountUpdateRequest,
    RoleAssignmentData,
    RoleAssignmentRequest,
)
from app.schemas.common import ApiResponse, PageData

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(
    principal: CurrentPrincipal,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[PageData[AccountData]]:
    """Return account summaries for R04 without exposing credential material."""
    require_system_role(principal, "R04")

    total = db.scalar(select(func.count()).select_from(User)) or 0
    accounts = db.scalars(
        select(User)
        .order_by(User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    account_ids = [account.id for account in accounts]

    system_roles_by_user: dict[int, list[str]] = defaultdict(list)
    club_roles_by_user: dict[int, list[dict[str, int | str]]] = defaultdict(list)
    if account_ids:
        for user_id, role_code in db.execute(
            select(SystemRoleAssignment.user_id, SystemRoleAssignment.role_code).where(
                SystemRoleAssignment.user_id.in_(account_ids),
                SystemRoleAssignment.active.is_(True),
            )
        ).all():
            system_roles_by_user[user_id].append(role_code)
        for user_id, club_id in db.execute(
            select(ClubRoleAssignment.user_id, ClubRoleAssignment.club_id).where(
                ClubRoleAssignment.user_id.in_(account_ids),
                ClubRoleAssignment.role_code == "R02",
                ClubRoleAssignment.active.is_(True),
            )
        ).all():
            club_roles_by_user[user_id].append({"club_id": club_id, "role_code": "R02"})

    return ApiResponse(
        data=PageData(
            items=[
                AccountData(
                    user_id=account.id,
                    username=account.username,
                    display_name=account.display_name,
                    status=account.status.value,
                    system_roles=sorted(system_roles_by_user[account.id]),
                    club_authorizations=club_roles_by_user[account.id],
                )
                for account in accounts
            ],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


@router.post("")
def create_account(
    principal: CurrentPrincipal,
    body: AccountCreateRequest,
    db: DbSession,
) -> ApiResponse[AccountData]:
    """Create a local test account with the non-revocable R01 base identity."""
    require_system_role(principal, "R04")
    if db.scalar(select(User.id).where(User.username == body.username)) is not None:
        raise AppError(40902, "用户名已存在", 409)

    account = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        status=AccountStatus.NORMAL,
    )
    db.add(account)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(40902, "用户名已存在", 409) from exc

    db.add(SystemRoleAssignment(user_id=account.id, role_code="R01", active=True, granted_by=principal.user_id))
    db.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="ACCOUNT_CREATED",
            resource_type="USER",
            resource_id=str(account.id),
            detail_json=json.dumps({"username": account.username}, ensure_ascii=False),
        )
    )
    db.commit()
    return ApiResponse(
        data=AccountData(
            user_id=account.id,
            username=account.username,
            display_name=account.display_name,
            status=account.status.value,
            system_roles=["R01"],
            club_authorizations=[],
        )
    )


@router.patch("/{account_id}")
def update_account(
    account_id: int,
    principal: CurrentPrincipal,
    body: AccountUpdateRequest,
    db: DbSession,
) -> ApiResponse[AccountData]:
    """Update local test-account profile/status without deleting historical data."""
    require_system_role(principal, "R04")
    account = db.get(User, account_id)
    if account is None:
        raise AppError(40401, "账号不存在", 404)

    changes: dict[str, str] = {}
    if body.display_name is not None and body.display_name != account.display_name:
        account.display_name = body.display_name
        changes["display_name"] = body.display_name
    if body.status is not None:
        requested_status = AccountStatus(body.status)
        if requested_status != account.status:
            account.status = requested_status
            changes["status"] = requested_status.value
    if not changes:
        raise AppError(40901, "账号资料或状态未发生变化", 409)

    db.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="ACCOUNT_UPDATED",
            resource_type="USER",
            resource_id=str(account.id),
            detail_json=json.dumps(changes, ensure_ascii=False),
        )
    )
    db.commit()

    system_roles = sorted(
        db.scalars(
            select(SystemRoleAssignment.role_code).where(
                SystemRoleAssignment.user_id == account.id,
                SystemRoleAssignment.active.is_(True),
            )
        ).all()
    )
    club_authorizations = [
        {"club_id": club_id, "role_code": "R02"}
        for club_id in db.scalars(
            select(ClubRoleAssignment.club_id).where(
                ClubRoleAssignment.user_id == account.id,
                ClubRoleAssignment.role_code == "R02",
                ClubRoleAssignment.active.is_(True),
            )
        ).all()
    ]
    return ApiResponse(
        data=AccountData(
            user_id=account.id,
            username=account.username,
            display_name=account.display_name,
            status=account.status.value,
            system_roles=system_roles,
            club_authorizations=club_authorizations,
        )
    )


@router.post("/{account_id}/role-assignments")
def grant_role(
    account_id: int,
    body: RoleAssignmentRequest,
    principal: CurrentPrincipal,
    db: DbSession,
) -> ApiResponse[RoleAssignmentData]:
    """Grant a resource-scoped R02 or a system-scoped R03/R04 authorization."""
    require_system_role(principal, "R04")
    account = db.get(User, account_id)
    if account is None:
        raise AppError(40401, "账号不存在", 404)

    if body.role_code == "R02":
        if body.club_id is None:
            raise AppError(40002, "授予 R02 必须指定社团", 400)
        if db.get(Club, body.club_id) is None:
            raise AppError(40401, "社团不存在", 404)
        assignment = db.scalar(
            select(ClubRoleAssignment).where(
                ClubRoleAssignment.user_id == account_id,
                ClubRoleAssignment.club_id == body.club_id,
                ClubRoleAssignment.role_code == "R02",
            )
        )
        if assignment is not None and assignment.active:
            raise AppError(40902, "该社团 R02 授权已存在", 409)
        if assignment is None:
            assignment = ClubRoleAssignment(
                user_id=account_id,
                club_id=body.club_id,
                role_code="R02",
                active=True,
                granted_by=principal.user_id,
            )
            db.add(assignment)
        else:
            assignment.active = True
            assignment.granted_by = principal.user_id
        granted_data = RoleAssignmentData(user_id=account_id, role_code="R02", club_id=body.club_id, active=True)
    else:
        if body.club_id is not None:
            raise AppError(40002, "R03 或 R04 不得指定社团", 400)
        assignment = db.scalar(
            select(SystemRoleAssignment).where(
                SystemRoleAssignment.user_id == account_id,
                SystemRoleAssignment.role_code == body.role_code,
            )
        )
        if assignment is not None and assignment.active:
            raise AppError(40902, "系统角色授权已存在", 409)
        if assignment is None:
            assignment = SystemRoleAssignment(
                user_id=account_id,
                role_code=body.role_code,
                active=True,
                granted_by=principal.user_id,
            )
            db.add(assignment)
        else:
            assignment.active = True
            assignment.granted_by = principal.user_id
        granted_data = RoleAssignmentData(user_id=account_id, role_code=body.role_code, active=True)

    db.add(
        AuditLog(
            actor_user_id=principal.user_id,
            action="ROLE_GRANTED",
            resource_type="ROLE_ASSIGNMENT",
            resource_id=str(account_id),
            detail_json=json.dumps(granted_data.model_dump(), ensure_ascii=False),
        )
    )
    db.commit()
    return ApiResponse(data=granted_data)


@router.delete("/{account_id}/role-assignments/{role_code}")
def revoke_system_role(account_id: int, role_code: str, _: CurrentPrincipal):
    todo("FR-23", "Leader/Integration")


@router.delete("/{account_id}/club-role-assignments/{club_id}")
def revoke_club_role(account_id: int, club_id: int, _: CurrentPrincipal):
    todo("FR-23", "Leader/Integration")
