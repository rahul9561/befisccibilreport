"""Score panel and the static score-range explanation panel."""

from __future__ import annotations

from typing import Sequence

from ..config import Theme
from ..models import Score
from .base import Block, wrap_runs


class ScorePanel(Block):
    """One shaded row per score: name, large score value, numbered factors."""

    NAME_X, NAME_BASELINE = 5.0, 13.0
    VALUE_BASELINE = 16.3
    FACTOR_NUM_GAP = 8.7
    FACTOR_FIRST, FACTOR_PITCH = 9.5, 7.1
    MIN_H, BOTTOM_PAD = 21.6, 5.0

    def __init__(self, theme: Theme, scores: Sequence[Score], value_x: float, factors_x: float) -> None:
        super().__init__(theme)
        self.scores = list(scores) or [Score()]
        self.value_x = value_x
        self.factors_x = factors_x
        self.keepWithNext = False

    def measure(self, width: float) -> float:
        self._rows = []
        fw = width - self.factors_x - self.FACTOR_NUM_GAP - 4
        total = 0.0
        for sc in self.scores:
            factors = []
            for i, f in enumerate(sc.factors, start=1):
                lines = wrap_runs([self.s.regular(f)], fw)
                factors.append((f"{i}.", lines))
            n_lines = sum(len(l) for _, l in factors)
            h = max(self.MIN_H, self.FACTOR_FIRST + max(n_lines - 1, 0) * self.FACTOR_PITCH + self.BOTTOM_PAD)
            self._rows.append((sc, factors, h))
            total += h
        return total

    def paint(self, width: float, height: float) -> None:
        p, t = self.theme.palette, self.theme.type
        top = 0.0
        for sc, factors, h in self._rows:
            self.rect(0, top, width, h, p.panel)
            self.text_at(self.NAME_X, top + self.NAME_BASELINE, self.s.bold(sc.name, color=p.accent_dark))
            self.text_at(self.value_x, top + self.VALUE_BASELINE, self.s.regular(sc.value, color=p.accent_dark, size=t.score))
            baseline = top + self.FACTOR_FIRST
            for num, lines in factors:
                self.text_at(self.factors_x, baseline, self.s.regular(num))
                self.lines_at(self.factors_x + self.FACTOR_NUM_GAP, baseline, lines, self.FACTOR_PITCH)
                baseline += len(lines) * self.FACTOR_PITCH
            top += h


class ScoreRangePanel(Block):
    """Static explanation of the score range (template text, not data)."""

    X = 5.0
    TITLE_BASELINE = 9.5
    ROWS_FIRST, ROW_PITCH = 17.2, 7.5
    NOTE_GAP = 10.7
    BOTTOM_PAD = 5.0

    def __init__(self, theme: Theme, title: str, rows: Sequence[tuple[str, str]], note: str,
                 value_x: float, space_before: float = 9.2) -> None:
        super().__init__(theme)
        self.title = title
        self.rows = list(rows)
        self.note = note
        self.value_x = value_x
        self.spaceBefore = space_before

    def measure(self, width: float) -> float:
        last_row = self.ROWS_FIRST + (len(self.rows) - 1) * self.ROW_PITCH
        self._note_baseline = last_row + self.NOTE_GAP
        return self._note_baseline + self.BOTTOM_PAD

    def paint(self, width: float, height: float) -> None:
        p = self.theme.palette
        self.rect(0, 0, width, height, p.panel)
        self.text_at(self.X, self.TITLE_BASELINE, self.s.bold(self.title, color=p.accent_dark))
        for i, (label, value) in enumerate(self.rows):
            b = self.ROWS_FIRST + i * self.ROW_PITCH
            self.text_at(self.X, b, self.s.bold(label))
            self.text_at(self.value_x, b, self.s.bold(value, color=p.alert))
        self.text_at(self.X, self._note_baseline, self.s.bold(self.note))
