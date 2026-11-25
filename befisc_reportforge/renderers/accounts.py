"""ACCOUNT(S) and ENQUIRIES detail sections, and the closing disclaimer."""

from __future__ import annotations

from reportlab.platypus import KeepTogether

from ..components import (
    AccountBlock, GridPanel, HeadedGroup, Rule, SectionTitle, Styler, TextBlock, ZebraTable,
)
from ..models import CreditReport
from .base import RenderContext, section

DISCLAIMER = (
    "All information contained in this credit report has been collated by TransUnion CIBIL Limited "
    "(TU CIBIL) based on information provided / submitted by its various members (“Members”), as "
    "part of periodic data submission and Members are required to ensure accuracy, completeness and "
    "veracity of the information submitted. The credit report is generated using the proprietary search "
    "and match logic of TU CIBIL. TU CIBIL uses its best efforts to ensure accuracy, completeness and "
    "veracity of the information contained in the Report, and shall only be liable and / or responsible "
    "if any discrepancies are directly attributable to TU CIBIL. The use of this report is governed by "
    "the terms and conditions of the Operating Rules for TU CIBIL and its Members."
)
COPYRIGHT_LINES = (
    "© 2018 TransUnion CIBIL Limited. (Formerly: Credit Information Bureau (India) Limited). All rights reserved",
    "TransUnion CIBIL CIN : U72300MH2000PLC128359",
)


@section("accounts")
def render_accounts(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    title = SectionTitle(th, "ACCOUNT(S):", below=6.0)
    if not report.accounts:
        return [HeadedGroup([title], GridPanel(th, ctx.cols(1), None, [[[[s.value("No accounts reported")]]]]))]
    gap = th.geometry.account_gap
    blocks = [AccountBlock(th, acc, i, space_before=gap if i else 0.0, frame_height=ctx.frame_height)
              for i, acc in enumerate(report.accounts)]
    return [HeadedGroup([title], blocks[0]), *blocks[1:]]


@section("enquiries")
def render_enquiries(report: CreditReport, ctx: RenderContext) -> list:
    th = ctx.theme
    rows = [[e.member, e.date, e.purpose, e.amount] for e in report.enquiries]
    return [HeadedGroup(
        [SectionTitle(th, "ENQUIRIES:", gap=13.7)],
        ZebraTable(th, ["MEMBER", "ENQUIRY DATE", "ENQUIRY PURPOSE", "ENQUIRY AMOUNT"], rows),
    )]


@section("disclaimer")
def render_disclaimer(report: CreditReport, ctx: RenderContext) -> list:
    th, s = ctx.theme, Styler(ctx.theme)
    return [
        TextBlock(th, [[s.bold(DISCLAIMER)]], leading=7.07, first_baseline=5.0,
                  space_before=10.7, bottom_pad=0.0),
        KeepTogether([
            Rule(th, 1.5, th.palette.footer_rule, space_before=8.45),
            TextBlock(th, [[s.bold(line)] for line in COPYRIGHT_LINES], leading=10.7,
                      first_baseline=11.05, centered=True, bottom_pad=2.0),
        ]),
    ]
