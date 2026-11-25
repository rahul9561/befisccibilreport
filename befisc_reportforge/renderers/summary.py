"""SUMMARY section: account and enquiry totals."""

from __future__ import annotations

from ..calculations import format_amount
from ..components import GridPanel, HeadedGroup, SectionTitle, Styler, SubHeading
from ..models import CreditReport
from .base import RenderContext, section


def _d(value) -> str:
    return value.isoformat() if value else ""


@section("summary")
def render_summary(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    a, e = report.account_summary, report.enquiry_summary
    account_row = [
        [[s.value("All Accounts")]],
        [s.field("TOTAL:", str(a.total)), s.field("OVERDUE:", str(a.overdue_count)),
         s.field("ZERO-BALANCE:", str(a.zero_balance_count))],
        [s.field("HIGH CR/SANC. AMT:", format_amount(a.high_credit_total))],
        [s.field("CURRENT:", format_amount(a.current_balance_total)),
         s.field("OVERDUE:", format_amount(a.overdue_total))],
        [s.field("RECENT:", _d(a.most_recent_opened)), s.field("OLDEST:", _d(a.oldest_opened))],
    ]
    enquiry_row = [
        [[s.value("All Enquiries")]],
        [[s.value(str(e.total))]],
        [[s.value(str(e.past_30_days))]],
        [[s.value(str(e.past_12_months))]],
        [[s.value(str(e.past_24_months))]],
        [[s.value(_d(e.most_recent))]],
    ]
    return [
        HeadedGroup(
            [SectionTitle(th, "SUMMARY:"), SubHeading(th, "ACCOUNT(S)")],
            GridPanel(th, ctx.cols(5, reduce=4.0),
                      ["ACCOUNT TYPE", "ACCOUNTS", "ADVANCES", "BALANCES", "DATE OPENED"], [account_row]),
        ),
        HeadedGroup(
            [SubHeading(th, "ENQUIRIES", space_before=10.0)],
            GridPanel(th, ctx.cols(6, reduce=4.0),
                      ["ENQUIRY PURPOSE", "TOTAL", "PAST 30 DAYS", "PAST 12 MONTHS", "PAST 24 MONTHS", "RECENT"],
                      [enquiry_row]),
        ),
    ]
