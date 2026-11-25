"""Derived summary values (SUMMARY section).

Rules
-----
* ``-1`` is the bureau's "not reported" sentinel and is excluded from every
  sum.  (The reference generator added the sentinels into OVERDUE, e.g.
  227550 + 4 x (-1) = 227546; treating them as missing is the correct reading.)
* Negative balances other than the sentinel (credit balances such as -179) are
  real values and are included.
* Enquiry windows are measured back from the report date and are inclusive:
  "past 30 days" counts enquiries on or after ``report_date - 30 days``;
  "past N months" counts those on or after the same calendar day N months ago.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Optional

from .models import Account, AccountSummary, Enquiry, EnquirySummary
from .utils.dates import months_before


def summarise_accounts(accounts: Iterable[Account]) -> AccountSummary:
    accounts = list(accounts)
    s = AccountSummary(total=len(accounts))
    opened: list[date] = []
    for acc in accounts:
        if acc.overdue_value is not None and acc.overdue_value > 0:
            s.overdue_count += 1
            s.overdue_total += acc.overdue_value
        if acc.current_balance_value is not None:
            s.current_balance_total += acc.current_balance_value
            if acc.current_balance_value == 0:
                s.zero_balance_count += 1
        if acc.high_credit_value is not None and acc.high_credit_value > 0:
            s.high_credit_total += acc.high_credit_value
        if acc.date_opened:
            opened.append(acc.date_opened)
    if opened:
        s.most_recent_opened = max(opened)
        s.oldest_opened = min(opened)
    return s


def summarise_enquiries(enquiries: Iterable[Enquiry], report_date: Optional[date]) -> EnquirySummary:
    enquiries = list(enquiries)
    s = EnquirySummary(total=len(enquiries))
    dates = [e.date_value for e in enquiries if e.date_value]
    if dates:
        s.most_recent = max(dates)
    if report_date is None:
        return s
    d30 = report_date - timedelta(days=30)
    m12 = months_before(report_date, 12)
    m24 = months_before(report_date, 24)
    for d in dates:
        if d > report_date:
            # Future-dated enquiries are still "recent".
            s.past_30_days += 1
            s.past_12_months += 1
            s.past_24_months += 1
            continue
        if d >= d30:
            s.past_30_days += 1
        if d >= m12:
            s.past_12_months += 1
        if d >= m24:
            s.past_24_months += 1
    return s


def format_amount(value: Decimal) -> str:
    """Amounts are printed as plain integers in the reference (no separators)."""
    if value == value.to_integral_value():
        return str(int(value))
    return f"{value:.2f}"
