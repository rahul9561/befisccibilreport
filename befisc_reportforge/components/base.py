"""Low-level building blocks shared by every component.

``Run``      a piece of text in one font/size/colour.
``wrap_runs`` greedy word-wrap of a sequence of runs into positioned lines,
             exactly like a browser/Typst inline layout (break at spaces, and
             inside a word only when the word alone is wider than the line).
``Block``    base Flowable: subclasses compute their height in ``measure`` and
             draw in local coordinates measured *downwards from the top* in
             ``paint``, which keeps geometry code readable and matches how
             offsets were measured from the reference PDF.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from reportlab.lib.colors import Color
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

from ..config import Theme
from ..utils.text import plain


@dataclass(frozen=True)
class Run:
    text: str
    font: str
    size: float
    color: Color
    # Fixed horizontal gap before this run when it follows another run
    # (None = a normal space in this run's font).
    gap_before: Optional[float] = None


@dataclass(frozen=True)
class Placed:
    x: float
    text: str
    font: str
    size: float
    color: Color


Line = list[Placed]


class Styler:
    """Builds runs in the theme's semantic styles."""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme
        self.f = theme.font
        self.p = theme.palette
        self.t = theme.type

    def _clean(self, value: str) -> str:
        return plain(value or "", builtin_font=self.f.is_builtin)

    def label(self, value: str) -> Run:
        return Run(self._clean(value), self.f.italic, self.t.body, self.p.label)

    def value(self, value: str) -> Run:
        return Run(self._clean(value), self.f.bold, self.t.body, self.p.text)

    def regular(self, value: str, color: Optional[Color] = None, size: Optional[float] = None) -> Run:
        return Run(self._clean(value), self.f.regular, size or self.t.body, color or self.p.text)

    def bold(self, value: str, color: Optional[Color] = None, size: Optional[float] = None) -> Run:
        return Run(self._clean(value), self.f.bold, size or self.t.body, color or self.p.text)

    def col_header(self, value: str) -> Run:
        return Run(self._clean(value), self.f.bold, self.t.column_header, self.p.column_header)

    def field(self, label: str, value: str) -> list[Run]:
        """``LABEL: value`` (italic grey label, bold black value)."""
        runs = [self.label(label)]
        if value:
            v = self.value(value)
            runs.append(Run(v.text, v.font, v.size, v.color, gap_before=self.t.label_gap))
        return runs


def _split_long(word: str, font: str, size: float, width: float) -> list[str]:
    parts, cur = [], ""
    for ch in word:
        if cur and stringWidth(cur + ch, font, size) > width:
            parts.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        parts.append(cur)
    return parts


def wrap_runs(runs: Sequence[Run], width: float) -> list[Line]:
    """Lay ``runs`` out in lines no wider than ``width``.

    Consecutive runs are separated by a single space in the first run's font
    (the reference puts a normal space between label and value).
    """
    tokens: list[tuple[str, Run, bool, bool]] = []  # (word, run, space_before, first_of_run)
    for i, run in enumerate(runs):
        first = True
        for w in run.text.split(" "):
            if not w:
                continue
            tokens.append((w, run, bool(tokens), first and i > 0))
            first = False

    lines: list[Line] = [[]]
    x = 0.0
    for word, run, space, run_start in tokens:
        ww = stringWidth(word, run.font, run.size)
        sw = 0.0
        if space and lines[-1]:
            if run_start and run.gap_before is not None:
                sw = run.gap_before
            else:
                sw = stringWidth(" ", run.font, run.size)
        if lines[-1] and x + sw + ww > width:
            lines.append([])
            x, sw = 0.0, 0.0
        if not lines[-1] and ww > width:
            pieces = _split_long(word, run.font, run.size, width)
            for k, piece in enumerate(pieces):
                if k:
                    lines.append([])
                lines[-1].append(Placed(0.0, piece, run.font, run.size, run.color))
            x = stringWidth(pieces[-1], run.font, run.size)
            continue
        x += sw
        lines[-1].append(Placed(x, word, run.font, run.size, run.color))
        x += ww
    return [ln for ln in lines if ln] or []


def line_width(line: Line) -> float:
    if not line:
        return 0.0
    last = line[-1]
    return last.x + stringWidth(last.text, last.font, last.size)


class Block(Flowable):
    """Flowable that lays out in top-down local coordinates."""

    def __init__(self, theme: Theme) -> None:
        super().__init__()
        self.theme = theme
        self.s = Styler(theme)
        self._height: Optional[float] = None
        self._width: float = 0.0

    # -- subclass API ---------------------------------------------------------
    def measure(self, width: float) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    def paint(self, width: float, height: float) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- Flowable protocol ----------------------------------------------------
    def wrap(self, availWidth: float, availHeight: float):  # noqa: N803 (ReportLab API)
        self._width = availWidth
        self._height = self.measure(availWidth)
        self.width, self.height = availWidth, self._height
        return availWidth, self._height

    def draw(self) -> None:
        self.paint(self._width, self._height or 0.0)

    # -- drawing helpers (y measured downward from block top) -----------------
    def y(self, top_offset: float) -> float:
        return (self._height or 0.0) - top_offset

    def text_at(self, x: float, baseline: float, run: Run) -> None:
        if not run.text:
            return
        c = self.canv
        c.setFont(run.font, run.size)
        c.setFillColor(run.color)
        c.drawString(x, self.y(baseline), run.text)

    def text_centered(self, cx: float, baseline: float, run: Run) -> None:
        if not run.text:
            return
        c = self.canv
        c.setFont(run.font, run.size)
        c.setFillColor(run.color)
        c.drawCentredString(cx, self.y(baseline), run.text)

    def lines_at(self, x: float, first_baseline: float, lines: Iterable[Line], leading: float) -> None:
        c = self.canv
        for i, line in enumerate(lines):
            yy = self.y(first_baseline + i * leading)
            for p in line:
                c.setFont(p.font, p.size)
                c.setFillColor(p.color)
                c.drawString(x + p.x, yy, p.text)

    def rect(self, x: float, top: float, w: float, h: float, color: Color) -> None:
        c = self.canv
        c.setFillColor(color)
        c.setStrokeColor(color)
        c.rect(x, self.y(top + h), w, h, stroke=0, fill=1)

    def hline(self, x0: float, x1: float, top_offset: float, width: float, color: Color) -> None:
        c = self.canv
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x0, self.y(top_offset), x1, self.y(top_offset))
