"""Keep section headings with the start of their content (no orphans).

ReportLab's ``keepWithNext`` wraps the heading and the *whole* next flowable
in ``KeepTogether``; for a long table that pushes the entire section to a new
page and leaves a large blank area.  ``HeadedGroup`` instead keeps the
heading(s) with only the first piece of a splittable body.
"""

from __future__ import annotations

from typing import Sequence

from reportlab.platypus import Flowable


class HeadedGroup(Flowable):
    def __init__(self, heads: Sequence[Flowable], body: Flowable) -> None:
        super().__init__()
        self.heads = list(heads)
        self.body = body
        self.spaceBefore = getattr(self.heads[0], "spaceBefore", 0) if self.heads else getattr(body, "spaceBefore", 0)
        for f in self.heads:
            f.keepWithNext = False

    def _children(self) -> list[Flowable]:
        return [*self.heads, self.body]

    def _gap(self, i: int, f: Flowable) -> float:
        return 0.0 if i == 0 else float(getattr(f, "spaceBefore", 0) or 0)

    def _heads_height(self, aw: float, ah: float) -> float:
        total = 0.0
        for i, f in enumerate(self.heads):
            _, h = f.wrap(aw, ah)
            total += h + self._gap(i, f)
        return total

    def wrap(self, availWidth: float, availHeight: float):  # noqa: N803
        heads_h = self._heads_height(availWidth, availHeight)
        _, bh = self.body.wrap(availWidth, max(availHeight - heads_h, 0))
        self.width = availWidth
        self.height = heads_h + bh + self._gap(len(self.heads), self.body)
        return availWidth, self.height

    def draw(self) -> None:
        y = self.height
        for i, f in enumerate(self._children()):
            y -= self._gap(i, f) + f.height
            f.drawOn(self.canv, 0, y)

    def split(self, availWidth: float, availHeight: float):  # noqa: N803
        heads_h = self._heads_height(availWidth, availHeight)
        room = availHeight - heads_h - self._gap(len(self.heads), self.body)
        if room <= 0:
            return []
        self.body.wrap(availWidth, room)
        parts = self.body.split(availWidth, room)
        if not parts:
            return []  # move heading and body to the next page together
        return [HeadedGroup(self.heads, parts[0]), *parts[1:]]
