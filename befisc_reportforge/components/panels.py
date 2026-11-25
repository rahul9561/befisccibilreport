"""Splittable panels and tables.

Every component here can break across pages between rows; continuation
pieces repeat their column headings so a reader never loses context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from reportlab.lib.colors import Color

from ..config import Theme
from .base import Block, Line, Run, wrap_runs

Paragraph = Sequence[Run]
Cell = Sequence[Paragraph]


def _layout_cell(cell: Cell, width: float) -> list[Line]:
    lines: list[Line] = []
    for para in cell:
        lines.extend(wrap_runs(para, width))
    return lines


@dataclass(frozen=True)
class Column:
    x: float
    width: float


class GridPanel(Block):
    """Shaded panel: a row of cyan column headings followed by data rows."""

    def __init__(
        self,
        theme: Theme,
        columns: Sequence[Column],
        headers: Optional[Sequence[str]],
        rows: Sequence[Sequence[Cell]],
        fill: Optional[Color] = None,
        space_before: float = 0.0,
        header_baseline: float = 8.1,
        header_to_rows: float = 7.5,
        bottom_pad: Optional[float] = None,
        empty_text: str = "",
    ) -> None:
        super().__init__(theme)
        self.columns = list(columns)
        self.headers = list(headers) if headers else None
        self.rows = [list(r) for r in rows]
        self.fill = fill if fill is not None else theme.palette.panel
        self.spaceBefore = space_before
        self.header_baseline = header_baseline
        self.header_to_rows = header_to_rows
        self.bottom_pad = theme.geometry.panel_bottom_pad if bottom_pad is None else bottom_pad
        self.empty_text = empty_text
        self.leading = theme.type.leading
        self._kw = dict(
            fill=self.fill, header_baseline=header_baseline, header_to_rows=header_to_rows,
            bottom_pad=self.bottom_pad,
        )

    # -- layout ---------------------------------------------------------------
    def _layout(self) -> None:
        hl = self.theme.type.header_leading
        self._header_lines = []
        header_lines = 1
        if self.headers:
            for col, label in zip(self.columns, self.headers):
                lines = wrap_runs([self.s.col_header(label)], col.width - 2)
                self._header_lines.append((col.x, lines))
                header_lines = max(header_lines, len(lines))
            self._first_row = self.header_baseline + (header_lines - 1) * hl + self.header_to_rows
        else:
            self._first_row = self.header_baseline
        self._row_layout = []
        for row in self.rows:
            cells = [(col.x, _layout_cell(cell, col.width - 2)) for col, cell in zip(self.columns, row)]
            n = max((len(lines) for _, lines in cells), default=1) or 1
            self._row_layout.append((cells, n))

    def _height_for(self, n_rows: int) -> float:
        lines = sum(n for _, n in self._row_layout[:n_rows])
        if lines == 0:
            last = self._first_row - (self.header_to_rows if self.headers else 0)
            if self.empty_text:
                last = self._first_row
            return last + self.bottom_pad
        return self._first_row + (lines - 1) * self.leading + self.bottom_pad

    def measure(self, width: float) -> float:
        self._layout()
        return self._height_for(len(self.rows))

    def paint(self, width: float, height: float) -> None:
        self.rect(0, 0, width, height, self.fill)
        hl = self.theme.type.header_leading
        for x, lines in self._header_lines:
            self.lines_at(x, self.header_baseline, lines, hl)
        baseline = self._first_row
        if not self.rows and self.empty_text:
            self.text_at(self.columns[0].x, baseline, self.s.value(self.empty_text))
        for cells, n in self._row_layout:
            for x, lines in cells:
                self.lines_at(x, baseline, lines, self.leading)
            baseline += n * self.leading

    # -- pagination -----------------------------------------------------------
    def split(self, availWidth: float, availHeight: float):  # noqa: N803
        self.wrap(availWidth, availHeight)
        fit = 0
        for i in range(1, len(self.rows) + 1):
            if self._height_for(i) <= availHeight:
                fit = i
            else:
                break
        if fit == 0 or fit >= len(self.rows):
            return []
        first = GridPanel(self.theme, self.columns, self.headers, self.rows[:fit],
                          space_before=self.spaceBefore, **self._kw)
        rest = GridPanel(self.theme, self.columns, self.headers, self.rows[fit:], **self._kw)
        return [first, rest]


class StripedRows(Block):
    """Rows separated by small gaps with alternating backgrounds (ADDRESS(ES))."""

    def __init__(
        self,
        theme: Theme,
        rows: Sequence[Sequence[tuple[float, float, Paragraph]]],
        first_baseline: float = 7.5,
        line_pitch: float = 7.7,
        bottom_pad: float = 3.0,
        gap: float = 2.0,
        start_index: int = 0,
        space_before: float = 0.0,
    ) -> None:
        """``rows``: per row, a list of (x, line_index, runs) placements.

        Placements on line 0 may wrap (address text); the later lines shift
        down by however many extra lines the wrap produced.
        """
        super().__init__(theme)
        self.rows = [list(r) for r in rows]
        self.first_baseline = first_baseline
        self.line_pitch = line_pitch
        self.bottom_pad = bottom_pad
        self.gap = gap
        self.start_index = start_index
        self.spaceBefore = space_before

    def _row_layout(self, width: float):
        out = []
        for row in self.rows:
            max_line = max((int(li) for _, li, _ in row), default=0)
            extra = 0
            placed = []
            for x, li, runs in sorted(row, key=lambda r: r[1]):
                lines = wrap_runs(runs, width - x - 4)
                if li == 0:
                    extra = max(extra, len(lines) - 1)
                placed.append((x, li, lines))
            height = self.first_baseline + (max_line + extra) * self.line_pitch + self.bottom_pad
            out.append((placed, extra, height))
        return out

    def measure(self, width: float) -> float:
        self._layout = self._row_layout(width)
        if not self._layout:
            return 0.0
        return sum(h for _, _, h in self._layout) + self.gap * (len(self._layout) - 1)

    def paint(self, width: float, height: float) -> None:
        p = self.theme.palette
        top = 0.0
        for i, (placed, extra, h) in enumerate(self._layout):
            color = p.stripe if (self.start_index + i) % 2 == 0 else p.white
            self.rect(0, top, width, h, color)
            for x, li, lines in placed:
                shift = 0 if li == 0 else extra
                self.lines_at(x, top + self.first_baseline + (li + shift) * self.line_pitch, lines, self.line_pitch)
            top += h + self.gap

    def split(self, availWidth: float, availHeight: float):  # noqa: N803
        self.wrap(availWidth, availHeight)
        used, fit = 0.0, 0
        for i, (_, _, h) in enumerate(self._layout):
            need = h + (self.gap if i else 0)
            if used + need > availHeight:
                break
            used += need
            fit += 1
        if fit == 0 or fit >= len(self.rows):
            return []
        kw = dict(first_baseline=self.first_baseline, line_pitch=self.line_pitch,
                  bottom_pad=self.bottom_pad, gap=self.gap)
        return [
            StripedRows(self.theme, self.rows[:fit], start_index=self.start_index, space_before=self.spaceBefore, **kw),
            StripedRows(self.theme, self.rows[fit:], start_index=self.start_index + fit, **kw),
        ]


class ZebraTable(Block):
    """Plain table with a white heading row and zebra-striped body rows."""

    HEADER_H, HEADER_BASELINE = 9.1, 6.6
    ROW_H, ROW_BASELINE = 9.47, 7.0
    INSET = 3.0

    def __init__(self, theme: Theme, headers: Sequence[str], rows: Sequence[Sequence[str]],
                 start_index: int = 0, space_before: float = 0.0) -> None:
        super().__init__(theme)
        self.headers = list(headers)
        self.rows = [list(r) for r in rows]
        self.start_index = start_index
        self.spaceBefore = space_before

    def _layout(self, width: float) -> None:
        n = len(self.headers)
        self._colw = width / n
        self._rows = []
        for row in self.rows:
            cells = [wrap_runs([self.s.value(v)], self._colw - 2 * self.INSET) for v in row]
            lines = max((len(c) for c in cells), default=1) or 1
            self._rows.append((cells, self.ROW_H + (lines - 1) * self.theme.type.leading))

    def measure(self, width: float) -> float:
        self._layout(width)
        return self.HEADER_H + sum(h for _, h in self._rows)

    def paint(self, width: float, height: float) -> None:
        p = self.theme.palette
        self.rect(0, 0, width, self.HEADER_H, p.white)
        for i, label in enumerate(self.headers):
            self.text_at(i * self._colw + self.INSET, self.HEADER_BASELINE, self.s.col_header(label))
        top = self.HEADER_H
        for r, (cells, h) in enumerate(self._rows):
            color = p.stripe if (self.start_index + r) % 2 == 0 else p.white
            self.rect(0, top, width, h, color)
            for i, lines in enumerate(cells):
                self.lines_at(i * self._colw + self.INSET, top + self.ROW_BASELINE, lines, self.theme.type.leading)
            top += h

    def split(self, availWidth: float, availHeight: float):  # noqa: N803
        self.wrap(availWidth, availHeight)
        used, fit = self.HEADER_H, 0
        for _, h in self._rows:
            if used + h > availHeight:
                break
            used += h
            fit += 1
        if fit == 0 or fit >= len(self.rows):
            return []
        return [
            ZebraTable(self.theme, self.headers, self.rows[:fit], self.start_index, self.spaceBefore),
            ZebraTable(self.theme, self.headers, self.rows[fit:], self.start_index + fit),
        ]
