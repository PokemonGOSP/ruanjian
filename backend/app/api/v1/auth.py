from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import create_access_token
from app.db.models.domain import Club, ClubRoleAssignment, RevokedToken
from app.schemas.auth import CurrentUserData, LoginRequest, TokenData
from app.schemas.common import ApiResponse
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[TokenData])
def login(body: LoginRequest, db: DbSession) -> dict:
    user = authenticate_user(db, body.username, body.password)
    if user is None:
        raise AppError(40104, "用户名或密码错误", 401)
    token, _, _ = create_access_token(user.id, user.username)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": get_settings().access_token_expire_minutes * 60,
        },
    }


@router.post("/logout", response_model=ApiResponse[dict])
def logout(principal: CurrentPrincipal, db: DbSession) -> dict:
    if principal.token_jti and principal.token_expires_at:
        db.add(
            RevokedToken(
                jti=principal.token_jti,
                user_id=principal.user_id,
                expires_at=datetime.fromtimestamp(principal.token_expires_at, UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    return {"code": 0, "message": "success", "data": {}}


@router.get("/me", response_model=ApiResponse[CurrentUserData])
def me(principal: CurrentPrincipal, db: DbSession) -> dict:
    club_rows = db.execute(
        select(Club.id, Club.name)
        .join(ClubRoleAssignment, ClubRoleAssignment.club_id == Club.id)
        .where(
            ClubRoleAssignment.user_id == principal.user_id,
            ClubRoleAssignment.role_code == "R02",
            ClubRoleAssignment.active.is_(True),
        )
    ).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "user_id": principal.user_id,
            "username": principal.username,
            "display_name": principal.display_name,
            "system_roles": sorted(principal.system_roles),
            "club_authorizations": [
                {"club_id": row.id, "club_name": row.name, "role_code": "R02"} for row in club_rows
            ],
        },
    }
