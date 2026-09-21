from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.api.v1.skeleton import todo
from app.schemas.business import PayloadRequest, ReasonRequest

router = APIRouter(prefix="/finance-records", tags=["finance"])
# TODO(Member C): implement M05 records and summaries; do not add payment or approval.


@router.get("/summary")
def finance_summary(_: CurrentPrincipal, club_id: int | None = None):
    todo("FR-18", "Member C")


@router.post("")
def create_finance_record(_: CurrentPrincipal, body: PayloadRequest):
    todo("FR-17", "Member C")


@router.get("")
def list_finance_records(_: CurrentPrincipal, page: int = 1, page_size: int = 20):
    todo("FR-18", "Member C")


@router.patch("/{record_id}")
def update_finance_record(record_id: int, _: CurrentPrincipal, body: PayloadRequest):
    todo("FR-17", "Member C")


@router.post("/{record_id}/void")
def void_finance_record(record_id: int, _: CurrentPrincipal, body: ReasonRequest):
    todo("FR-17", "Member C")
