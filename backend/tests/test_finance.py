from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.db.models.domain import FinanceType, RecordStatus
from app.schemas.finance import FinanceRecordUpdateRequest
from app.services import finance_service
from app.services.club_scope import resolve_club_scope


class FakeClubDb:
    def __init__(self, existing: set[int]):
        self.existing = existing

    def get(self, _model, key):
        return SimpleNamespace(id=key) if key in self.existing else None


def test_r02_cannot_read_other_club_scope(r02):
    db = FakeClubDb({1, 2, 3})
    with pytest.raises(AppError) as exc:
        resolve_club_scope(db, r02, 2)
    assert exc.value.code == 40302


def test_r02_scope_is_own_clubs(r02):
    db = FakeClubDb({1, 2, 3})
    assert resolve_club_scope(db, r02, None) == [1, 3]
    assert resolve_club_scope(db, r02, 1) == [1]


def test_r03_scope_is_all_clubs(r03):
    db = FakeClubDb({1, 2, 3})
    assert resolve_club_scope(db, r03, None) is None
    assert resolve_club_scope(db, r03, 2) == [2]


def test_r01_has_no_finance_scope(r01):
    db = FakeClubDb({1})
    with pytest.raises(AppError) as exc:
        resolve_club_scope(db, r01, None)
    assert exc.value.code == 40301


def test_missing_club_returns_404(r03):
    db = FakeClubDb({1})
    with pytest.raises(AppError) as exc:
        resolve_club_scope(db, r03, 99)
    assert exc.value.code == 40401


class FakeRecord:
    id = 1
    club_id = 1
    status = RecordStatus.ACTIVE


class FakeRecordDb:
    def get(self, _model, _key):
        return FakeRecord()


def test_update_rejects_explicit_null_for_required_field(r02):
    with pytest.raises(AppError) as exc:
        finance_service.update_record(
            FakeRecordDb(),
            r02,
            1,
            FinanceRecordUpdateRequest(amount=None),
        )
    assert exc.value.code == 40002


def test_build_csv_has_bom_crlf_and_formula_guard():
    records = [
        {
            "id": 1,
            "club_name": "星河读书社",
            "activity_title": None,
            "record_type": FinanceType.EXPENSE,
            "amount": Decimal("12.50"),
            "occurred_on": datetime(2026, 10, 1, 9, 30),
            "description": "=SUM(A1:A2)",
            "voucher_reference": "+voucher",
            "status": RecordStatus.ACTIVE,
            "created_by_name": "负责人一",
            "voided_by_name": None,
            "void_reason": None,
            "created_at": datetime(2026, 10, 1, 10, 0),
        }
    ]
    summary = {
        "income_total": Decimal("100.00"),
        "expense_total": Decimal("12.50"),
        "balance": Decimal("87.50"),
        "active_record_count": 1,
        "voided_record_count": 0,
    }
    payload = finance_service.build_csv(
        records,
        summary,
        scope_label="星河读书社",
        generated_at="2026-10-27 12:00:00",
    )
    assert payload.startswith(b"\xef\xbb\xbf")
    text = payload.decode("utf-8-sig")
    assert "\r\n" in text
    assert "经费汇总" in text
    assert "收入合计,100.00" in text
    assert "'=SUM(A1:A2)" in text
    assert "'+voucher" in text
    assert "支出" in text


def test_create_finance_record_rejects_r01(client, override_auth, override_db, r01):
    override_auth(r01)
    override_db(None)
    response = client.post(
        "/api/v1/finance-records",
        json={
            "club_id": 1,
            "record_type": "EXPENSE",
            "amount": "10.00",
            "occurred_on": "2026-10-01T00:00:00",
            "description": "测试支出",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == 40302


def test_create_finance_record_returns_domain_payload(client, monkeypatch, override_auth, override_db, r02):
    override_auth(r02)
    override_db(None)
    monkeypatch.setattr(
        finance_service,
        "create_record",
        lambda *args, **kwargs: {
            "id": 1,
            "club_id": 1,
            "club_name": "星河读书社",
            "activity_id": None,
            "activity_title": None,
            "record_type": "EXPENSE",
            "amount": "10.00",
            "occurred_on": "2026-10-01T00:00:00",
            "description": "测试支出",
            "voucher_reference": None,
            "status": "ACTIVE",
            "created_by": 3,
            "created_by_name": "社团负责人一",
            "voided_by": None,
            "voided_by_name": None,
            "void_reason": None,
            "created_at": "2026-10-01T00:00:00",
        },
    )
    response = client.post(
        "/api/v1/finance-records",
        json={
            "club_id": 1,
            "record_type": "EXPENSE",
            "amount": "10.00",
            "occurred_on": "2026-10-01T00:00:00",
            "description": "测试支出",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["club_name"] == "星河读书社"
    assert body["data"]["status"] == "ACTIVE"


def test_finance_amount_must_be_positive(client, override_auth, override_db, r02):
    override_auth(r02)
    override_db(None)
    response = client.post(
        "/api/v1/finance-records",
        json={
            "club_id": 1,
            "record_type": "EXPENSE",
            "amount": "0",
            "occurred_on": "2026-10-01T00:00:00",
            "description": "非法金额",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_list_finance_records_for_r03(client, monkeypatch, override_auth, override_db, r03):
    override_auth(r03)
    override_db(None)
    monkeypatch.setattr(finance_service, "list_records", lambda *args, **kwargs: ([], 0))
    response = client.get("/api/v1/finance-records")
    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "page": 1, "page_size": 20, "total": 0}
