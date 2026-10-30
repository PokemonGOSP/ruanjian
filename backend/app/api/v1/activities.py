"""M04 活动管理 API（FR-11～FR-16）。

Router 只负责 HTTP 契约、查询参数校验和统一响应封装；业务校验、状态转换和事务
提交由 `ActivityService` 完成。路径与 method 保持 `docs/api/API_CONTRACT_V0_1.md`。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.activity import ActivityData, RegistrationData
from app.schemas.business import (
    ActivityCreateRequest,
    ActivityEndRequest,
    ActivityUpdateRequest,
    ReasonRequest,
    ReviewRequest,
)
from app.schemas.common import ApiResponse, PageData
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


def get_activity_service(db: DbSession) -> ActivityService:
    return ActivityService(db)


ActivityServiceDep = Annotated[ActivityService, Depends(get_activity_service)]
PageQuery = Annotated[int, Query(ge=1)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]


def _ok(data) -> dict:
    return {"code": 0, "message": "success", "data": data}


@router.post("", response_model=ApiResponse[ActivityData])
def create_activity(
    principal: CurrentPrincipal, body: ActivityCreateRequest, service: ActivityServiceDep
) -> dict:
    return _ok(service.create(principal, body))


@router.get("", response_model=ApiResponse[PageData[ActivityData]])
def list_activities(
    principal: CurrentPrincipal,
    service: ActivityServiceDep,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
) -> dict:
    items, total = service.list(principal, page=page, page_size=page_size)
    return _ok({"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/{activity_id}", response_model=ApiResponse[ActivityData])
def get_activity(
    activity_id: int, principal: CurrentPrincipal, service: ActivityServiceDep
) -> dict:
    return _ok(service.get(principal, activity_id))


@router.patch("/{activity_id}", response_model=ApiResponse[ActivityData])
def update_activity(
    activity_id: int,
    principal: CurrentPrincipal,
    body: ActivityUpdateRequest,
    service: ActivityServiceDep,
) -> dict:
    return _ok(service.update(principal, activity_id, body))


@router.post("/{activity_id}/submit", response_model=ApiResponse[ActivityData])
def submit_activity(
    activity_id: int, principal: CurrentPrincipal, service: ActivityServiceDep
) -> dict:
    return _ok(service.submit(principal, activity_id))


@router.post("/{activity_id}/withdraw", response_model=ApiResponse[ActivityData])
def withdraw_activity(
    activity_id: int, principal: CurrentPrincipal, service: ActivityServiceDep
) -> dict:
    return _ok(service.withdraw(principal, activity_id))


@router.post("/{activity_id}/review", response_model=ApiResponse[ActivityData])
def review_activity(
    activity_id: int,
    principal: CurrentPrincipal,
    body: ReviewRequest,
    service: ActivityServiceDep,
) -> dict:
    return _ok(service.review(principal, activity_id, body))


@router.post("/{activity_id}/publish", response_model=ApiResponse[ActivityData])
def publish_activity(
    activity_id: int, principal: CurrentPrincipal, service: ActivityServiceDep
) -> dict:
    return _ok(service.publish(principal, activity_id))


@router.post(
    "/{activity_id}/registrations", response_model=ApiResponse[RegistrationData]
)
def register_activity(
    activity_id: int, principal: CurrentPrincipal, service: ActivityServiceDep
) -> dict:
    return _ok(service.register(principal, activity_id))


@router.delete("/{activity_id}/registrations/me", response_model=ApiResponse[dict])
def cancel_registration(
    activity_id: int, principal: CurrentPrincipal, service: ActivityServiceDep
) -> dict:
    return _ok(service.cancel_registration(principal, activity_id))


@router.get(
    "/{activity_id}/registrations", response_model=ApiResponse[PageData[RegistrationData]]
)
def list_registrations(
    activity_id: int,
    principal: CurrentPrincipal,
    service: ActivityServiceDep,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
) -> dict:
    items, total = service.list_registrations(
        principal, activity_id, page=page, page_size=page_size
    )
    return _ok({"items": items, "page": page, "page_size": page_size, "total": total})


@router.post("/{activity_id}/cancel", response_model=ApiResponse[ActivityData])
def cancel_activity(
    activity_id: int,
    principal: CurrentPrincipal,
    body: ReasonRequest,
    service: ActivityServiceDep,
) -> dict:
    return _ok(service.cancel(principal, activity_id, body.reason))


@router.post("/{activity_id}/end", response_model=ApiResponse[ActivityData])
def end_activity(
    activity_id: int,
    principal: CurrentPrincipal,
    body: ActivityEndRequest,
    service: ActivityServiceDep,
) -> dict:
    return _ok(service.end(principal, activity_id, body))
