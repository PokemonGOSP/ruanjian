from collections import defaultdict

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentPrincipal, DbSession
from app.api.v1.skeleton import todo
from app.core.permissions import require_system_role
from app.db.models.domain import ClubRoleAssignment, SystemRoleAssignment, User
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
def create_account(_: CurrentPrincipal, body: AccountCreateRequest):
    todo("FR-23", "Leader/Integration")


@router.patch("/{account_id}")
def update_account(account_id: int, _: CurrentPrincipal, body: AccountUpdateRequest):
    todo("FR-23", "Leader/Integration")


@router.post("/{account_id}/role-assignments")
def grant_role(account_id: int, _: CurrentPrincipal, body: RoleAssignmentRequest):
    todo("FR-23", "Leader/Integration")


@router.delete("/{account_id}/role-assignments/{role_code}")
def revoke_system_role(account_id: int, role_code: str, _: CurrentPrincipal):
    todo("FR-23", "Leader/Integration")


@router.delete("/{account_id}/club-role-assignments/{club_id}")
def revoke_club_role(account_id: int, club_id: int, _: CurrentPrincipal):
    todo("FR-23", "Leader/Integration")
