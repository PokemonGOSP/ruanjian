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
from app.db.models.domain import AccountStatus, AuditLog, ClubRoleAssignment, SystemRoleAssignment, User
from app.schemas.business import AccountCreateRequest, AccountData, AccountUpdateRequest, RoleAssignmentRequest
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
def grant_role(account_id: int, _: CurrentPrincipal, body: RoleAssignmentRequest):
    todo("FR-23", "Leader/Integration")


@router.delete("/{account_id}/role-assignments/{role_code}")
def revoke_system_role(account_id: int, role_code: str, _: CurrentPrincipal):
    todo("FR-23", "Leader/Integration")


@router.delete("/{account_id}/club-role-assignments/{club_id}")
def revoke_club_role(account_id: int, club_id: int, _: CurrentPrincipal):
    todo("FR-23", "Leader/Integration")
