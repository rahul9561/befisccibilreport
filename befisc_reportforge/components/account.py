"""Account (tradeline) block: four detail columns and the DPD history grid."""

from __future__ import annotations

from typing import Optional, Sequence

from ..config import Theme
from ..models import Account, PaymentStatus
from .base import Block, Line, wrap_runs

DPD_TITLE = "DAYS PAST DUE/ASSET CLASSIFICATION (UP TO 36 MONTHS; LEFT TO RIGHT)"


def account_columns(a: Account) -> list[tuple[str, list[tuple[str, str]]]]:
    """Field order and labels exactly as printed in the reference."""
    return [
        ("ACCOUNT", [
            ("MEMBER NAME:", a.member_name), ("ACCOUNT NUMBER:", a.account_number),
            ("TYPE:", a.account_type), ("OWNERSHIP:", a.ownership),
            ("Amount Overdue:", a.amount_overdue), ("INTEREST RATE:", a.interest_rate),
        ]),
        ("DATES", [
            ("OPENED:", a.opened), ("REPORTED AND CERTIFIED:", a.reported),
            ("PMT HIST START:", a.pmt_hist_start), ("PMT HIST END:", a.pmt_hist_end),
            ("LAST PAYMENT:", a.last_payment), ("COLLATERAL TYPE:", a.collateral_type),
        ]),
        ("AMOUNTS", [
            ("HIGH CREDIT AMOUNT:", a.high_credit), ("CREDIT LIMIT:", a.credit_limit),
            ("ACTUAL PAYMENT AMOUNT:", a.actual_payment), ("CURRENT BALANCE:", a.current_balance),
            ("EMI:", a.emi), ("PAYMENT FREQUENCY:", a.payment_frequency),
            ("REPAYMENT TENURE:", a.repayment_tenure), ("COLLATERAL VALUE:", a.collateral_value),
        ]),
        ("STATUS", [
            ("CREDIT FACILITY STATUS:", a.credit_facility_status), ("ACCOUNT CLOSED:", a.account_closed),
            ("WRITTEN-OFF AMOUNT(PRINCIPAL):", a.written_off_principal),
            ("WRITTEN-OFF AMOUNT(TOTAL):", a.written_off_total),
            ("SETTLEMENT AMOUNT:", a.settlement_amount),
            ("SUIT - FILED / WILFUL DEFAULT:", a.suit_filed), ("CASH LIMIT:", a.cash_limit),
        ]),
    ]


class AccountBlock(Block):
    # Geometry measured from the reference (offsets from block top / content left).
    HEADER_X = (3.0, 140.8, 278.6, 416.5)
    VALUE_X = (3.0, 142.8, 282.6, 422.5)
    COL_WIDTH = 134.0
    HEADER_BASELINE = 8.1
    FIRST_ROW = 18.8
    DPD_TITLE_GAP = 10.4
    DPD_FIRST_GAP = 12.7
    DPD_MONTH_GAP = 7.1
    BOTTOM_PAD = 6.0

    def __init__(self, theme: Theme, account: Account, index: int, *,
                 history: Optional[Sequence[PaymentStatus]] = None,
                 show_details: bool = True, space_before: float = 0.0,
                 frame_height: Optional[float] = None) -> None:
        super().__init__(theme)
        self.frame_height = frame_height
        self.account = account
        self.index = index
        self.history = list(account.payment_history if history is None else history)
        self.show_details = show_details
        self.spaceBefore = space_before
        g = theme.geometry
        self.per_row = g.dpd_cells_per_row
        self.cell_w = g.dpd_cell_width
        self.row_pitch = g.dpd_row_pitch
        self.rule_w = g.account_rule_width

    # -- layout ---------------------------------------------------------------
    def _detail_layout(self) -> tuple[list[tuple[float, float, str, list[Line]]], float]:
        cols = []
        max_lines = 0
        for (title, fields), hx, vx in zip(account_columns(self.account), self.HEADER_X, self.VALUE_X):
            lines: list[Line] = []
            for label, value in fields:
                lines.extend(wrap_runs(self.s.field(label, value), self.COL_WIDTH))
            cols.append((hx, vx, title, lines))
            max_lines = max(max_lines, len(lines))
        last = self.FIRST_ROW + (max_lines - 1) * self.theme.type.leading
        return cols, last

    def _dpd_rows(self, history: Sequence[PaymentStatus]) -> list[list[PaymentStatus]]:
        return [list(history[i:i + self.per_row]) for i in range(0, len(history), self.per_row)]

    def _content_height(self, n_dpd_rows: int) -> float:
        if self.show_details:
            _, last = self._detail_layout()
            title = last + self.DPD_TITLE_GAP
        else:
            title = self.HEADER_BASELINE
        if n_dpd_rows == 0:
            return title + self.BOTTOM_PAD
        last_month = title + self.DPD_FIRST_GAP + (n_dpd_rows - 1) * self.row_pitch + self.DPD_MONTH_GAP
        return last_month + self.BOTTOM_PAD

    def measure(self, width: float) -> float:
        self._content_h = self._content_height(len(self._dpd_rows(self.history)))
        return self._content_h + self.rule_w / 2

    # -- drawing --------------------------------------------------------------
    def paint(self, width: float, height: float) -> None:
        p = self.theme.palette
        bg = p.stripe if self.index % 2 == 0 else p.white
        self.rect(0, 0, width, self._content_h, bg)

        if self.show_details:
            cols, last = self._detail_layout()
            for hx, vx, title, lines in cols:
                self.text_at(hx, self.HEADER_BASELINE, self.s.col_header(title))
                self.lines_at(vx, self.FIRST_ROW, lines, self.theme.type.leading)
            title_baseline = last + self.DPD_TITLE_GAP
        else:
            title_baseline = self.HEADER_BASELINE
        self.text_at(self.VALUE_X[0], title_baseline, self.s.col_header(DPD_TITLE))

        first = title_baseline + self.DPD_FIRST_GAP
        center0 = self.VALUE_X[0] + self.cell_w / 2
        for r, row in enumerate(self._dpd_rows(self.history)):
            b = first + r * self.row_pitch
            for i, cell in enumerate(row):
                cx = center0 + i * self.cell_w
                self.text_centered(cx, b, self.s.value(cell.status))
                self.text_centered(cx, b + self.DPD_MONTH_GAP, self.s.value(cell.month))

        self.hline(0, width, self._content_h, self.rule_w, p.thin_rule)

    # -- pagination -----------------------------------------------------------
    def split(self, availWidth: float, availHeight: float):  # noqa: N803
        """Keep the block whole when possible; otherwise break between DPD rows.

        Returning ``[]`` makes ReportLab move the whole block to the next page.
        Only a block taller than an entire frame is broken.
        """
        rows = self._dpd_rows(self.history)
        whole = self._content_height(len(rows)) + self.rule_w / 2
        if self.frame_height is None or whole <= self.frame_height:
            return []
        fit = 0
        for n in range(1, len(rows)):
            if self._content_height(n) + self.rule_w / 2 <= availHeight:
                fit = n
        if fit == 0:
            return []
        cut = fit * self.per_row
        head = AccountBlock(self.theme, self.account, self.index, history=self.history[:cut],
                            show_details=self.show_details, space_before=self.spaceBefore,
                            frame_height=self.frame_height)
        tail = AccountBlock(self.theme, self.account, self.index, history=self.history[cut:],
                            show_details=False, frame_height=self.frame_height)
        return [head, tail]
