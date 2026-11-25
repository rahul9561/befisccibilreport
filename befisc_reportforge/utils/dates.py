"""Date parsing for the several formats bureaus emit."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_COMPACT = re.compile(r"^\d{8}$")


def parse_date(value: Any) -> Optional[date]:
    """Parse ``2026-04-08``, ``2026-04-08+05:30``, ``2026-04-08T11:24:36+05:30``,
    ``20260408`` (YYYYMMDD) or ``24112026`` (DDMMYYYY).  Invalid input -> ``None``.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    m = _ISO_DATE.match(raw)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if _COMPACT.match(raw):
            # Prefer YYYYMMDD; fall back to DDMMYYYY.
            y, mo, d = int(raw[:4]), int(raw[4:6]), int(raw[6:])
            if 1900 <= y <= 2200 and 1 <= mo <= 12:
                return date(y, mo, d)
            return date(int(raw[4:]), int(raw[2:4]), int(raw[:2]))
    except ValueError:
        return None
    return None


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp, keeping the wall-clock time it was written in."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    candidate = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        pass
    # Python 3.10 cannot parse milliseconds with offsets like "+05:30" in all
    # forms; strip fractional seconds and retry.
    candidate = re.sub(r"\.\d+", "", candidate)
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        d = parse_date(raw)
        return datetime(d.year, d.month, d.day) if d else None


def fmt_date(value: Any) -> str:
    d = parse_date(value)
    return d.isoformat() if d else ""


def fmt_month(value: Any) -> str:
    """``MM-YY`` label used under DPD cells."""
    d = parse_date(value)
    return d.strftime("%m-%y") if d else ""


def fmt_time(value: Optional[datetime]) -> str:
    return value.strftime("%I:%M %p") if value else ""


def months_before(ref: date, months: int) -> date:
    """Same day ``months`` months earlier, clamped to the month's last day."""
    y, m = divmod(ref.year * 12 + (ref.month - 1) - months, 12)
    m += 1
    for day in (ref.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise ValueError("unreachable")
