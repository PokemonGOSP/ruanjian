from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services import finance_service, report_service


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeScalarsResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSummaryDb:
    def __init__(self):
        self.scalars_in_order = iter(
            [2, 5, 3, 2, 3, 1, Decimal("500.00"), Decimal("88.00")]
        )
        self.executes_in_order = iter(
            [
                [("APPROVED", 2), ("REJECTED", 1)],
                [("REGISTRATION_OPEN", 1), ("ENDED", 1), ("CANCELLED", 1)],
            ]
        )

    def scalar(self, _stmt):
        return next(self.scalars_in_order)

    def execute(self, _stmt):
        return FakeResult(next(self.executes_in_order))

    def scalars(self, _stmt):
        return FakeScalarsResult([1, 3])

    def get(self, _model, key):
        return SimpleNamespace(id=key)


def test_build_summary_aggregates_counts_and_finance(r03):
    data = report_service.build_summary(FakeSummaryDb(), r03)
    assert data["club_count"] == 2
    assert data["member_count"] == 5
    assert data["activity_count"] == 3
    assert data["registration_count"] == 2
    assert data["activity_by_review_status"]["APPROVED"] == 2
    assert data["activity_by_review_status"]["DRAFT"] == 0
    assert data["activity_by_execution_status"]["ENDED"] == 1
    assert data["activity_by_execution_status"]["UNPUBLISHED"] == 0
    assert data["finance_income_total"] == Decimal("500.00")
    assert data["finance_expense_total"] == Decimal("88.00")
    assert data["finance_balance"] == Decimal("412.00")
    assert data["finance_voided_count"] == 1
    assert data["club_ids"] == [1, 3]

def test_audit_logs_require_r04(client, override_auth, override_db, r03):
    override_auth(r03)
    override_db(None)
    response = client.get("/api/v1/audit-logs")
    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_audit_logs_for_r04(client, monkeypatch, override_auth, override_db, r04):
    override_auth(r04)
    override_db(None)
    monkeypatch.setattr(report_service, "list_audit_logs", lambda *args, **kwargs: ([], 0))
    response = client.get("/api/v1/audit-logs")
    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "page": 1, "page_size": 20, "total": 0}


def test_report_summary_shape(client, monkeypatch, override_auth, override_db, r02):
    override_auth(r02)
    override_db(None)
    monkeypatch.setattr(
        report_service,
        "build_summary",
        lambda *args, **kwargs: {
            "club_id": None,
            "club_ids": [1, 3],
            "date_from": None,
            "date_to": None,
            "club_count": 2,
            "member_count": 5,
            "activity_count": 3,
            "registration_count": 2,
            "activity_by_review_status": {"DRAFT": 0, "PENDING": 0, "APPROVED": 2, "REJECTED": 1, "WITHDRAWN": 0},
            "activity_by_execution_status": {
                "UNPUBLISHED": 0,
                "REGISTRATION_OPEN": 1,
                "REGISTRATION_CLOSED": 0,
                "IN_PROGRESS": 0,
                "ENDED": 1,
                "CANCELLED": 1,
            },
            "finance_income_total": "500.00",
            "finance_expense_total": "88.00",
            "finance_balance": "412.00",
            "finance_voided_count": 1,
        },
    )
    response = client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["club_count"] == 2
    assert data["finance_balance"] == "412.00"


def test_export_rejects_unknown_format(client, override_auth, override_db, r02):
    override_auth(r02)
    override_db(None)
    response = client.get("/api/v1/reports/export", params={"format": "json"})
    assert response.status_code == 422
    assert response.json()["code"] == 40001


def test_export_csv_stream(client, monkeypatch, override_auth, override_db, r02):
    override_auth(r02)
    override_db(None)
    monkeypatch.setattr(
        finance_service,
        "export_csv",
        lambda *args, **kwargs: ("\ufeff经费汇总\r\n".encode("utf-8"), "finance-records.csv"),
    )
    response = client.get("/api/v1/reports/export", params={"format": "csv"})
    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["content-disposition"] == 'attachment; filename="finance-records.csv"'


# ---------------------------------------------------------------- Service 层
def test_build_summary_accepts_club_filter_and_dates(r03):
    data = report_service.build_summary(
        FakeSummaryDb(),
        r03,
        club_id=1,
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
    )
    assert data["club_id"] == 1
    assert data["club_ids"] == [1]
    assert data["date_from"] == date(2026, 10, 1)
    assert data["finance_balance"] == Decimal("412.00")


class FakeAuditDb:
    def __init__(self, rows, total=1):
        self.rows = rows
        self.total = total

    def scalar(self, _stmt):
        return self.total

    def execute(self, _stmt):
        return FakeResult(self.rows)


def make_audit_row(detail_json, row_id=1):
    return SimpleNamespace(
        id=row_id,
        actor_user_id=6,
        actor_username="admin01",
        action="FINANCE_RECORD_CREATED",
        resource_type="finance_record",
        resource_id="9",
        detail_json=detail_json,
        ip_address="127.0.0.1",
        created_at=datetime(2026, 10, 1, 9, 0),
    )


def test_list_audit_logs_parses_detail_json():
    rows = [
        make_audit_row('{"club_id": 1, "amount": "10.00"}', 1),
        make_audit_row("not-json", 2),
        make_audit_row(None, 3),
    ]
    items, total = report_service.list_audit_logs(FakeAuditDb(rows))

    assert total == 1
    assert items[0]["detail"] == {"club_id": 1, "amount": "10.00"}
    assert items[1]["detail"] == "not-json"
    assert items[2]["detail"] is None


def test_list_audit_logs_accepts_all_filters():
    rows = [make_audit_row('{"reason": "重复登记"}')]
    items, total = report_service.list_audit_logs(
        FakeAuditDb(rows, total=3),
        actor_user_id=6,
        action="FINANCE_RECORD_VOIDED",
        resource_type="finance_record",
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        page=2,
        page_size=10,
    )
    assert total == 3
    assert items[0]["action"] == "FINANCE_RECORD_CREATED"
    assert items[0]["detail"] == {"reason": "重复登记"}
