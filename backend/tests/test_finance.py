from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.db.models.domain import (
    Activity,
    AuditLog,
    Club,
    FinanceRecord,
    FinanceType,
    RecordStatus,
    User,
)
from app.schemas.finance import FinanceRecordCreateRequest, FinanceRecordUpdateRequest
from app.services import finance_service
from app.services.club_scope import resolve_club_scope
from tests.helpers import FakeDb


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


# ---------------------------------------------------------------- Service 层
def make_finance_db(*, club_id=1, activity_club_id=1) -> FakeDb:
    db = FakeDb()
    db.entities[(Club, club_id)] = SimpleNamespace(id=club_id, name="星河读书社")
    db.entities[(Activity, 5)] = SimpleNamespace(id=5, club_id=activity_club_id, title="读书会")
    db.entities[(User, 3)] = SimpleNamespace(id=3, display_name="社团负责人一")
    return db


def make_create_body(**overrides):
    payload = {
        "club_id": 1,
        "record_type": "EXPENSE",
        "amount": Decimal("35.50"),
        "occurred_on": datetime(2026, 10, 1, 9, 0),
        "description": "测试支出",
    }
    payload.update(overrides)
    return FinanceRecordCreateRequest(**payload)


def make_record(*, record_id=1, club_id=1, status=RecordStatus.ACTIVE):
    record = FinanceRecord(
        club_id=club_id,
        activity_id=None,
        record_type=FinanceType.EXPENSE,
        amount=Decimal("20.00"),
        occurred_on=datetime(2026, 10, 1, 9, 0),
        description="记录",
        voucher_reference=None,
        status=status,
        created_by=3,
    )
    record.id = record_id
    return record


def test_create_record_requires_club_leader(r01):
    with pytest.raises(AppError) as exc:
        finance_service.create_record(FakeDb(), r01, make_create_body())
    assert exc.value.code == 40302


def test_create_record_requires_existing_club(r02):
    with pytest.raises(AppError) as exc:
        finance_service.create_record(FakeDb(), r02, make_create_body())
    assert exc.value.code == 40401


def test_create_record_rejects_activity_from_other_club(r02):
    db = make_finance_db(activity_club_id=2)
    with pytest.raises(AppError) as exc:
        finance_service.create_record(db, r02, make_create_body(activity_id=5))
    assert exc.value.code == 40002


def test_create_record_persists_audit_and_serializes(r02):
    db = make_finance_db()
    data = finance_service.create_record(db, r02, make_create_body(activity_id=5))

    assert data["club_name"] == "星河读书社"
    assert data["activity_title"] == "读书会"
    assert data["created_by_name"] == "社团负责人一"
    assert data["status"] == "ACTIVE"
    assert db.commits == 1
    audits = db.objects(AuditLog)
    assert len(audits) == 1
    assert audits[0].action == "FINANCE_RECORD_CREATED"


def test_update_record_missing_returns_404(r02):
    with pytest.raises(AppError) as exc:
        finance_service.update_record(FakeDb(), r02, 99, FinanceRecordUpdateRequest(amount=Decimal("1.00")))
    assert exc.value.code == 40401


def test_update_record_requires_leader(r01):
    db = FakeDb()
    db.entities[(FinanceRecord, 1)] = make_record()
    with pytest.raises(AppError) as exc:
        finance_service.update_record(db, r01, 1, FinanceRecordUpdateRequest(amount=Decimal("1.00")))
    assert exc.value.code == 40302


def test_update_record_rejects_voided(r02):
    db = FakeDb()
    db.entities[(FinanceRecord, 1)] = make_record(status=RecordStatus.VOIDED)
    with pytest.raises(AppError) as exc:
        finance_service.update_record(db, r02, 1, FinanceRecordUpdateRequest(amount=Decimal("1.00")))
    assert exc.value.code == 40901


def test_update_record_rejects_empty_body(r02):
    db = FakeDb()
    db.entities[(FinanceRecord, 1)] = make_record()
    with pytest.raises(AppError) as exc:
        finance_service.update_record(db, r02, 1, FinanceRecordUpdateRequest())
    assert exc.value.code == 40002


def test_update_record_rejects_activity_from_other_club(r02):
    db = make_finance_db(activity_club_id=2)
    db.entities[(FinanceRecord, 1)] = make_record()
    with pytest.raises(AppError) as exc:
        finance_service.update_record(db, r02, 1, FinanceRecordUpdateRequest(activity_id=5))
    assert exc.value.code == 40002


def test_update_record_changes_type_amount_and_audits(r02):
    db = make_finance_db()
    record = make_record()
    record.activity_id = 5
    db.entities[(FinanceRecord, 1)] = record

    data = finance_service.update_record(
        db,
        r02,
        1,
        FinanceRecordUpdateRequest(record_type="INCOME", amount=Decimal("99.00"), voucher_reference=None),
    )

    assert record.record_type == FinanceType.INCOME
    assert record.amount == Decimal("99.00")
    assert record.voucher_reference is None
    assert data["amount"] == Decimal("99.00")
    assert db.commits == 1
    audits = db.objects(AuditLog)
    assert audits[0].action == "FINANCE_RECORD_UPDATED"


def test_void_record_missing_returns_404(r02):
    with pytest.raises(AppError) as exc:
        finance_service.void_record(FakeDb(), r02, 99, "重复登记")
    assert exc.value.code == 40401


def test_void_record_requires_leader(r01):
    db = FakeDb()
    db.entities[(FinanceRecord, 1)] = make_record()
    with pytest.raises(AppError) as exc:
        finance_service.void_record(db, r01, 1, "重复登记")
    assert exc.value.code == 40302


def test_void_record_rejects_already_voided(r02):
    db = FakeDb()
    db.entities[(FinanceRecord, 1)] = make_record(status=RecordStatus.VOIDED)
    with pytest.raises(AppError) as exc:
        finance_service.void_record(db, r02, 1, "重复登记")
    assert exc.value.code == 40901


def test_void_record_marks_voided_and_audits(r02):
    db = make_finance_db()
    record = make_record()
    db.entities[(FinanceRecord, 1)] = record

    data = finance_service.void_record(db, r02, 1, "重复登记")

    assert record.status == RecordStatus.VOIDED
    assert record.voided_by == r02.user_id
    assert record.void_reason == "重复登记"
    assert data["voided_by"] == r02.user_id
    assert db.objects(AuditLog)[0].action == "FINANCE_RECORD_VOIDED"


def test_export_csv_uses_club_names_for_leader_scope(r02, monkeypatch):
    monkeypatch.setattr(finance_service, "totals", lambda *args, **kwargs: {
        "income_total": Decimal("0"),
        "expense_total": Decimal("0"),
        "balance": Decimal("0"),
        "active_record_count": 0,
        "voided_record_count": 0,
    })
    monkeypatch.setattr(finance_service, "_all_records", lambda *args, **kwargs: [])
    db = FakeDb()
    db.scalars_result = ["星河读书社", "晨风运动社"]

    payload, filename = finance_service.export_csv(db, r02)

    assert filename == "finance-records.csv"
    text = payload.decode("utf-8-sig")
    assert "星河读书社、晨风运动社" in text


def test_export_csv_uses_all_clubs_label_for_r03(r03, monkeypatch):
    monkeypatch.setattr(finance_service, "totals", lambda *args, **kwargs: {
        "income_total": Decimal("0"),
        "expense_total": Decimal("0"),
        "balance": Decimal("0"),
        "active_record_count": 0,
        "voided_record_count": 0,
    })
    monkeypatch.setattr(finance_service, "_all_records", lambda *args, **kwargs: [])

    payload, _ = finance_service.export_csv(FakeDb(), r03)

    assert "全部社团" in payload.decode("utf-8-sig")
