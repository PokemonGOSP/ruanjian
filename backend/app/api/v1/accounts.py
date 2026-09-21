from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import AccountCreateRequest, AccountUpdateRequest, RoleAssignmentRequest

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-23", "Leader/Integration")


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
