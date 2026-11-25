"""Logo, "CONSUMER CIR" bar and report header (consumer / date / control number)."""

from __future__ import annotations

import logging

from ..components import FieldColumns, Logo, Styler, TitleBar
from ..exceptions import AssetError
from ..models import CreditReport
from ..utils.dates import fmt_time
from .base import RenderContext, section

log = logging.getLogger(__name__)

RIGHT_COLUMN_X = 284.6


@section("logo")
def render_logo(report: CreditReport, ctx: RenderContext) -> list:
    path = ctx.config.resolved_logo()
    try:
        return [Logo(ctx.theme, path)]
    except AssetError as exc:
        if ctx.config.strict:
            raise
        log.warning("logo skipped: %s", exc)
        report.warnings.append(f"logo skipped: {exc}")
        return []


@section("header")
def render_header(report: CreditReport, ctx: RenderContext) -> list:
    th = ctx.theme
    s = Styler(th)
    h = report.header
    left = [
        s.field("CONSUMER:", h.consumer_name),
        s.field("MEMBER ID:", h.member_id),
        s.field("MEMBER REFERENCE NUMBER:", h.member_reference),
    ]
    right = [
        s.field("DATE:", h.report_date.isoformat() if h.report_date else ""),
        s.field("TIME:", fmt_time(h.report_time)),
        s.field("CONTROL NUMBER:", h.control_number),
    ]
    width = ctx.frame_width
    return [
        TitleBar(th, ctx.config.running_header_text),
        FieldColumns(
            th,
            [(0.0, RIGHT_COLUMN_X - 4, left), (RIGHT_COLUMN_X, width - RIGHT_COLUMN_X, right)],
            first_baseline=7.8, leading=7.45,
            rule_gap=3.3, rule_width=2.5, rule_color=th.palette.header_rule,
        ),
    ]
