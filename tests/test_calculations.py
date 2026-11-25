from datetime import date
from decimal import Decimal

from befisc_reportforge.calculations import format_amount, summarise_accounts, summarise_enquiries
from befisc_reportforge.models import Account, Enquiry


def acc(opened=None, high=None, bal=None, overdue=None) -> Account:
    d = lambda v: None if v is None else Decimal(v)  # noqa: E731
    return Account(date_opened=opened, high_credit_value=d(high), current_balance_value=d(bal),
                   overdue_value=d(overdue))


def test_account_summary_rules():
    s = summarise_accounts([
        acc(date(2020, 1, 1), 1000, 0, 0),
        acc(date(2022, 5, 1), 5000, 2500, 300),
        acc(date(2019, 3, 3), 2000, -179, None),   # credit balance counts; sentinel overdue skipped
        acc(None, None, None, None),               # nothing reported
    ])
    assert s.total == 4
    assert s.overdue_count == 1 and s.overdue_total == Decimal(300)
    assert s.zero_balance_count == 1
    assert s.high_credit_total == Decimal(8000)
    assert s.current_balance_total == Decimal(2321)
    assert (s.most_recent_opened, s.oldest_opened) == (date(2022, 5, 1), date(2019, 3, 3))


def test_empty_summaries():
    s = summarise_accounts([])
    assert s.total == 0 and s.most_recent_opened is None
    e = summarise_enquiries([], date(2026, 1, 1))
    assert e.total == 0 and e.most_recent is None


def test_enquiry_windows_are_inclusive_and_relative_to_report_date():
    ref = date(2026, 11, 24)
    q = lambda d: Enquiry("M", d.isoformat(), "P", "1", d)  # noqa: E731
    e = summarise_enquiries([
        q(date(2026, 10, 25)),   # exactly 30 days back -> in 30d window
        q(date(2026, 10, 24)),   # 31 days back
        q(date(2025, 11, 24)),   # exactly 12 months back -> in 12m window
        q(date(2025, 11, 23)),
        q(date(2024, 11, 24)),   # exactly 24 months back
        q(date(2024, 11, 23)),
    ], ref)
    assert (e.total, e.past_30_days, e.past_12_months, e.past_24_months) == (6, 1, 3, 5)
    assert e.most_recent == date(2026, 10, 25)


def test_enquiries_without_report_date_still_count_total():
    e = summarise_enquiries([Enquiry("M", "", "P", "1", None)], None)
    assert e.total == 1 and e.past_30_days == 0


def test_format_amount():
    assert format_amount(Decimal("5278275")) == "5278275"
    assert format_amount(Decimal("-179")) == "-179"
    assert format_amount(Decimal("12.5")) == "12.50"
