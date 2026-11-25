"""IDENTIFICATION(S), TELEPHONE(S), EMAIL CONTACT(S), ADDRESS(ES), EMPLOYMENT."""

from __future__ import annotations

from ..components import GridPanel, HeadedGroup, SectionTitle, StripedRows, Styler
from ..models import CreditReport
from .base import RenderContext, section


def _cells(s: Styler, *values: str) -> list:
    return [[[s.value(v)]] if v else [] for v in values]


@section("identification")
def render_identification(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    rows = [_cells(s, i.label, i.number, i.issue_date, i.expiration_date) for i in report.identifications]
    panel = GridPanel(th, ctx.cols(4),
                      ["IDENTIFICATION TYPE", "IDENTIFICATION NUMBER", "ISSUE DATE", "EXPIRATION DATE"], rows)
    return [HeadedGroup([SectionTitle(th, "IDENTIFICATION(S):")], panel)]


@section("telephone")
def render_telephone(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    rows = [_cells(s, t.type, t.number, t.extension) for t in report.telephones]
    panel = GridPanel(th, ctx.cols(3), ["TELEPHONE TYPE", "TELEPHONE NUMBER", "TELEPHONE EXTENSION"], rows)
    return [HeadedGroup([SectionTitle(th, "TELEPHONE(S):")], panel)]


@section("email")
def render_email(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    rows = [_cells(s, e) for e in report.emails]
    panel = GridPanel(th, ctx.cols(1), ["EMAIL ADDRESS"], rows, header_to_rows=7.7)
    return [HeadedGroup([SectionTitle(th, "EMAIL CONTACT(S):")], panel)]


@section("address")
def render_address(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    rows = [
        [
            (3.0, 0, [s.col_header("ADDRESS :"), s.value(a.text)]),
            (3.0, 1, [s.col_header("CATEGORY:"), s.value(a.category)]),
            (170.8, 1, [s.col_header("RESIDENCE CODE:"), s.value(a.residence_code)]),
            (338.6, 1, [s.col_header("DATE REPORTED:"), s.value(a.date_reported)]),
        ]
        for a in report.addresses
    ]
    body = StripedRows(th, rows) if rows else GridPanel(
        th, ctx.cols(1), None, [[[[s.value("No addresses reported")]]]])
    return [HeadedGroup([SectionTitle(th, "ADDRESS(ES):")], body)]


@section("employment")
def render_employment(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    rows = [
        _cells(s, e.account_type, e.employer_name, e.date_reported, e.occupation, e.income,
               e.net_gross, e.monthly_annual)
        for e in report.employment
    ]
    headers = ["ACCOUNT TYPE", "EMPLOYER NAME", "DATE REPORTED", "OCCUPATION CODE", "INCOME",
               "NET / GROSS INCOME INDICATOR", "MONTHLY / ANNUAL INCOME INDICATOR"]
    panel = GridPanel(th, ctx.cols(7, reduce=4.0), headers, rows)
    return [HeadedGroup([SectionTitle(th, "EMPLOYMENT INFORMATION:")], panel)]
