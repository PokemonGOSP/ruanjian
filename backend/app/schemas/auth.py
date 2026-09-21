from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ClubAuthorizationSummary(BaseModel):
    club_id: int
    club_name: str
    role_code: str = "R02"


class CurrentUserData(BaseModel):
    user_id: int
    username: str
    display_name: str
    system_roles: list[str]
    club_authorizations: list[ClubAuthorizationSummary]
