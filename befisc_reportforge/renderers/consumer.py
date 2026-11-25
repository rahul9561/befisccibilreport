"""CONSUMER INFORMATION and CIBIL TRANSUNION SCORE(S) sections."""

from __future__ import annotations

from ..components import (
    ColumnHeaderRow, FieldColumns, HeadedGroup, ScorePanel, ScoreRangePanel, SectionTitle, Styler,
)
from ..models import CreditReport
from .base import RenderContext, section
from .header import RIGHT_COLUMN_X

SCORE_RANGE_TITLE = "POSSIBLE RANGE FOR CREDITVISION® SCORE"
SCORE_RANGE_ROWS = (
    ("Consumer with at least one trade on the bureau in last 36 months", ": 300 (high risk) to 900 (low risk)"),
    ("Consumer not in CIBIL database or history older than 36 months", ": -1"),
)
SCORE_RANGE_NOTE = "* At least one tradeline with information updated in last 36 months is required."


@section("consumer")
def render_consumer(report: CreditReport, ctx: RenderContext) -> list:
    th, s, c = ctx.theme, Styler(ctx.theme), report.consumer
    width = ctx.frame_width
    return [HeadedGroup(
        [SectionTitle(th, "CONSUMER INFORMATION:", gap=13.25, below=0.0)],
        FieldColumns(
            th,
            [
                (0.0, RIGHT_COLUMN_X - 4, [s.field("NAME:", c.name), s.field("DATE OF BIRTH:", c.date_of_birth)]),
                (RIGHT_COLUMN_X, width - RIGHT_COLUMN_X, [s.field("GENDER:", c.gender)]),
            ],
            first_baseline=9.4, leading=7.5,
            rule_gap=3.3, rule_width=0.5, rule_color=th.palette.thin_rule,
        ),
    )]


@section("score")
def render_score(report: CreditReport, ctx: RenderContext) -> list:
    th = ctx.theme
    col = ctx.frame_width / 4
    return [
        HeadedGroup(
            [SectionTitle(th, "CIBIL TRANSUNION SCORE(S):", gap=14.25, below=0.0),
             ColumnHeaderRow(th, [(0.0, "SCORE NAME"), (col, "SCORE"), (2 * col, "SCORING FACTORS")],
                             baseline=9.1, height=12.3)],
            ScorePanel(th, report.scores, value_x=col + 5.5, factors_x=2 * col + 6.0),
        ),
        ScoreRangePanel(th, SCORE_RANGE_TITLE, SCORE_RANGE_ROWS, SCORE_RANGE_NOTE, value_x=333.4),
    ]
