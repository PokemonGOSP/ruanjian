from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta


def naive_utc(value: datetime) -> datetime:
    """Store datetimes as naive UTC so MySQL DATETIME comparisons stay consistent."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def day_start(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min)


def day_end_exclusive(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value + timedelta(days=1), time.min)
