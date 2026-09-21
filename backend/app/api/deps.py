from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import Principal
from app.core.security import decode_access_token
from app.db.models.domain import AccountStatus, ClubRoleAssignment, RevokedToken, SystemRoleAssignment, User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_current_principal(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> Principal:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        jti = str(payload["jti"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError(40101, "登录凭证无效或已过期", 401) from exc

    if db.scalar(select(RevokedToken.id).where(RevokedToken.jti == jti)) is not None:
        raise AppError(40102, "登录凭证已注销", 401)

    user = db.get(User, user_id)
    if user is None or user.status != AccountStatus.NORMAL:
        raise AppError(40103, "账号不存在或已停用", 401)

    system_roles = set(
        db.scalars(
            select(SystemRoleAssignment.role_code).where(
                SystemRoleAssignment.user_id == user_id,
                SystemRoleAssignment.active.is_(True),
            )
        ).all()
    )
    club_ids = set(
        db.scalars(
            select(ClubRoleAssignment.club_id).where(
                ClubRoleAssignment.user_id == user_id,
                ClubRoleAssignment.role_code == "R02",
                ClubRoleAssignment.active.is_(True),
            )
        ).all()
    )
    return Principal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        system_roles=system_roles,
        club_leader_ids=club_ids,
        token_jti=jti,
        token_expires_at=payload.get("exp"),
    )


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
