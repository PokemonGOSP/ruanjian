from dataclasses import dataclass, field


@dataclass(slots=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    system_roles: set[str] = field(default_factory=set)
    club_leader_ids: set[int] = field(default_factory=set)
    token_jti: str | None = None
    token_expires_at: int | None = None

    def has_system_role(self, role_code: str) -> bool:
        return role_code in self.system_roles

    def leads_club(self, club_id: int) -> bool:
        return club_id in self.club_leader_ids


def require_system_role(principal: Principal, role_code: str) -> None:
    from app.core.exceptions import AppError

    if not principal.has_system_role(role_code):
        raise AppError(40301, f"需要 {role_code} 权限", 403)


def require_club_leader(principal: Principal, club_id: int) -> None:
    from app.core.exceptions import AppError

    if not principal.leads_club(club_id):
        raise AppError(40302, "没有该社团的 R02 权限", 403)
