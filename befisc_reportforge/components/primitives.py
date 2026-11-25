"""Simple, non-splitting layout pieces: logo, bars, titles, rules, field columns."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence

from reportlab.graphics import renderPDF
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

from ..config import Theme
from ..exceptions import AssetError
from .base import Block, Run, wrap_runs

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------- images

@lru_cache(maxsize=16)
def _load_svg(path: str):
    from svglib.svglib import svg2rlg

    drawing = svg2rlg(path)
    if drawing is None:
        raise AssetError(f"SVG could not be parsed: {path}")
    return drawing


class Logo(Block):
    """SVG (vector), PNG or JPG image scaled to a fixed width."""

    SUPPORTED = {".svg", ".png", ".jpg", ".jpeg"}

    def __init__(self, theme: Theme, path: Path, width: Optional[float] = None) -> None:
        super().__init__(theme)
        self.path = Path(path)
        self.target_width = width or theme.geometry.logo_width
        suffix = self.path.suffix.lower()
        if not self.path.is_file():
            raise AssetError(f"Logo file not found: {self.path}")
        if suffix not in self.SUPPORTED:
            raise AssetError(f"Unsupported logo format {suffix!r}; use one of {sorted(self.SUPPORTED)}")
        self.kind = "svg" if suffix == ".svg" else "raster"
        if self.kind == "svg":
            d = _load_svg(str(self.path))
            self.src_w, self.src_h = float(d.width), float(d.height)
        else:
            try:
                self.image = ImageReader(str(self.path))
            except Exception as exc:  # ReportLab raises many types for bad images
                raise AssetError(f"Image could not be read: {self.path} ({exc})") from exc
            self.src_w, self.src_h = (float(v) for v in self.image.getSize())
        self.scale = self.target_width / self.src_w

    def measure(self, width: float) -> float:
        return self.src_h * self.scale

    def paint(self, width: float, height: float) -> None:
        c = self.canv
        if self.kind == "svg":
            c.saveState()
            c.scale(self.scale, self.scale)
            renderPDF.draw(_load_svg(str(self.path)), c, 0, 0)
            c.restoreState()
        else:
            c.drawImage(self.image, 0, 0, self.target_width, height, mask="auto")


# ----------------------------------------------------------------------------- bars/titles

class TitleBar(Block):
    """Full-width coloured bar with a title (the yellow "CONSUMER CIR" bar)."""

    HEIGHT, BASELINE, INSET = 14.8, 10.8, 4.0

    def __init__(self, theme: Theme, title: str, space_before: float = 9.2) -> None:
        super().__init__(theme)
        self.title = title
        self.spaceBefore = space_before

    def measure(self, width: float) -> float:
        return self.HEIGHT

    def paint(self, width: float, height: float) -> None:
        self.rect(0, 0, width, height, self.theme.palette.title_bar)
        self.text_at(self.INSET, self.BASELINE, self.s.regular(self.title, size=self.theme.type.title_bar))


class SectionTitle(Block):
    """Grey uppercase section heading, kept with the block that follows it."""

    ASCENT = 6.0

    def __init__(self, theme: Theme, title: str, gap: Optional[float] = None, below: Optional[float] = None) -> None:
        super().__init__(theme)
        self.title = title
        gap = theme.geometry.section_gap if gap is None else gap
        self.below = theme.geometry.title_to_panel if below is None else below
        self.spaceBefore = max(gap - self.ASCENT, 0)
        self.keepWithNext = True

    def measure(self, width: float) -> float:
        return self.ASCENT + self.below

    def paint(self, width: float, height: float) -> None:
        p, t = self.theme.palette, self.theme.type
        self.text_at(0, self.ASCENT, self.s.bold(self.title, color=p.heading, size=t.section_title))


class SubHeading(Block):
    """Small cyan heading inside a section (e.g. "ACCOUNT(S)" in SUMMARY)."""

    ASCENT, BELOW = 4.8, 3.5

    def __init__(self, theme: Theme, title: str, space_before: float = 0.0) -> None:
        super().__init__(theme)
        self.title = title
        self.spaceBefore = space_before
        self.keepWithNext = True

    def measure(self, width: float) -> float:
        return self.ASCENT + self.BELOW

    def paint(self, width: float, height: float) -> None:
        p, t = self.theme.palette, self.theme.type
        self.text_at(0, self.ASCENT, self.s.bold(self.title, color=p.column_header, size=t.sub_heading))


class ColumnHeaderRow(Block):
    """Cyan column headings drawn outside a panel (score section)."""

    def __init__(self, theme: Theme, headers: Sequence[tuple[float, str]], baseline: float = 4.1, height: float = 7.3) -> None:
        super().__init__(theme)
        self.headers = headers
        self.baseline = baseline
        self._h = height
        self.keepWithNext = True

    def measure(self, width: float) -> float:
        return self._h

    def paint(self, width: float, height: float) -> None:
        for x, label in self.headers:
            self.text_at(x, self.baseline, self.s.col_header(label))


class FieldColumns(Block):
    """Columns of ``LABEL: value`` lines with an optional rule underneath.

    Used for the report header (consumer / date / control number) and for the
    CONSUMER INFORMATION block.
    """

    def __init__(
        self,
        theme: Theme,
        columns: Sequence[tuple[float, float, Sequence[Sequence[Run]]]],
        first_baseline: float,
        leading: float,
        rule_gap: float = 3.3,
        rule_width: float = 0.0,
        rule_color: Optional[Color] = None,
        bottom_pad: float = 3.3,
    ) -> None:
        super().__init__(theme)
        self.columns = columns  # (x, width, paragraphs)
        self.first_baseline = first_baseline
        self.leading = leading
        self.rule_gap = rule_gap
        self.rule_width = rule_width
        self.rule_color = rule_color
        self.bottom_pad = bottom_pad
        self._laid: list = []

    def measure(self, width: float) -> float:
        self._laid = []
        max_lines = 1
        for x, w, paras in self.columns:
            lines = []
            for runs in paras:
                lines.extend(wrap_runs(runs, w) or [[]])
            self._laid.append((x, lines))
            max_lines = max(max_lines, len(lines))
        last = self.first_baseline + (max_lines - 1) * self.leading
        if self.rule_width:
            self._rule_at = last + self.rule_gap
            return self._rule_at + self.rule_width / 2
        return last + self.bottom_pad

    def paint(self, width: float, height: float) -> None:
        for x, lines in self._laid:
            self.lines_at(x, self.first_baseline, lines, self.leading)
        if self.rule_width:
            self.hline(0, width, self._rule_at, self.rule_width, self.rule_color)


class TextBlock(Block):
    """Wrapped paragraph(s), optionally centred, with an optional rule above."""

    def __init__(
        self,
        theme: Theme,
        paragraphs: Sequence[Sequence[Run]],
        leading: float,
        first_baseline: float,
        centered: bool = False,
        space_before: float = 0.0,
        bottom_pad: float = 3.0,
    ) -> None:
        super().__init__(theme)
        self.paragraphs = paragraphs
        self.leading = leading
        self.first_baseline = first_baseline
        self.centered = centered
        self.spaceBefore = space_before
        self.bottom_pad = bottom_pad

    def measure(self, width: float) -> float:
        self._lines = []
        for runs in self.paragraphs:
            self._lines.extend(wrap_runs(runs, width))
        return self.first_baseline + max(len(self._lines) - 1, 0) * self.leading + self.bottom_pad

    def paint(self, width: float, height: float) -> None:
        from .base import line_width

        for i, line in enumerate(self._lines):
            offset = (width - line_width(line)) / 2 if self.centered else 0.0
            self.lines_at(offset, self.first_baseline + i * self.leading, [line], self.leading)


class Rule(Block):
    """Full-width horizontal rule occupying its own line width."""

    def __init__(self, theme: Theme, width: float, color: Color, space_before: float = 0.0) -> None:
        super().__init__(theme)
        self.line_width = width
        self.color = color
        self.spaceBefore = space_before

    def measure(self, width: float) -> float:
        return self.line_width

    def paint(self, width: float, height: float) -> None:
        self.hline(0, width, height / 2, self.line_width, self.color)
