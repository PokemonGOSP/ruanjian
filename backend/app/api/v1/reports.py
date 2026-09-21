from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo

router = APIRouter(tags=["reports"])
# TODO(Member C): implement M07 reports and audit queries with existing role boundaries.


@router.get("/reports/summary")
def report_summary(_: CurrentPrincipal):
    todo("FR-21", "Member C")


@router.get("/reports/export")
def export_report(_: CurrentPrincipal, format: str = "csv"):
    todo("FR-21", "Member C")


@router.get("/audit-logs")
def list_audit_logs(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-22", "Member C")
