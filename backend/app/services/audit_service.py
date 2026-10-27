from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models.domain import AuditLog


def record_audit(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
    detail: Any | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add one audit row. The caller owns the surrounding transaction/commit."""
    row = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail_json=json.dumps(detail, ensure_ascii=False, default=str) if detail is not None else None,
        ip_address=ip_address,
    )
    db.add(row)
    return row


def request_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host[:45]
