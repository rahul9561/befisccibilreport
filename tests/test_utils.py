from datetime import date, datetime
from decimal import Decimal

from befisc_reportforge.components.base import Run, wrap_runs
from befisc_reportforge.data.codes import ACCOUNT_TYPE, OWNERSHIP, lookup
from befisc_reportforge.utils import (
    as_list, dig, fmt_date, fmt_month, fmt_time, is_reported, months_before, parse_date, parse_datetime,
    text, to_number, to_winansi,
)
from reportlab.lib.colors import black


def test_dig_handles_missing_and_single_objects():
    data = {"a": {"b": [{"c": 1}]}, "x": {"y": 2}}
    assert dig(data, "a", "b", 0, "c") == 1
    assert dig(data, "a", "missing", default="d") == "d"
    assert dig(data, "x", 0, "y") == 2          # dict where a list was expected
    assert dig(None, "a") is None
    assert dig(data, "a", "b", 5) is None


def test_as_list_and_text():
    assert as_list(None) == []
    assert as_list({"k": 1}) == [{"k": 1}]
    assert as_list([1, None, 2]) == [1, 2]
    assert text(None) == "" and text({"a": 1}) == "" and text(5.0) == "5" and text("  x ") == "x"


def test_numbers_and_sentinel():
    assert to_number("1,234") == Decimal(1234)
    assert to_number("abc") is None and to_number("") is None
    assert not is_reported("-1") and not is_reported(None) and is_reported("0") and is_reported("-179")


def test_dates():
    assert parse_date("2026-04-08+05:30") == date(2026, 4, 8)
    assert parse_date("20260408") == date(2026, 4, 8)
    assert parse_date("24112026") == date(2026, 11, 24)
    assert parse_date("2026-02-30") is None and parse_date("") is None and parse_date("garbage") is None
    assert fmt_date("2026-04-08T10:00:00") == "2026-04-08"
    assert fmt_month("2026-09-01+05:30") == "09-26"
    dt = parse_datetime("2026-11-24T23:30:36.662+05:30")
    assert isinstance(dt, datetime) and fmt_time(dt) == "11:30 PM"
    assert months_before(date(2024, 3, 31), 1) == date(2024, 2, 29)
    assert months_before(date(2026, 11, 24), 24) == date(2024, 11, 24)


def test_code_lookup():
    assert lookup(ACCOUNT_TYPE, "05") == "Personal Loan"
    assert lookup(ACCOUNT_TYPE, "5") == "Personal Loan"       # zero-padding normalised
    assert lookup(OWNERSHIP, "01") == "Individual"
    assert lookup(ACCOUNT_TYPE, "ZZ") == "ZZ"                 # unknown -> raw, never dropped
    assert lookup(ACCOUNT_TYPE, "") == "" and lookup(ACCOUNT_TYPE, None) == ""


def test_winansi_guard():
    assert to_winansi("plain ©®“”") == "plain ©®“”"
    assert to_winansi("café") == "café"
    assert to_winansi("नमस्ते") == "??????"


def test_wrap_runs_breaks_words_and_long_tokens():
    run = Run("ONE TWO THREE FOUR", "Helvetica-Bold", 6.5, black)
    lines = wrap_runs([run], 40)
    assert len(lines) > 1 and all(lines)
    long = Run("X" * 200, "Helvetica-Bold", 6.5, black)
    assert len(wrap_runs([long], 50)) > 5
    assert wrap_runs([Run("", "Helvetica", 6.5, black)], 50) == []
