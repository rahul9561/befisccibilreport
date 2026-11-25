"""Page template: frame geometry, document metadata and page decorations.

Page decorations (running header, running footer, "Page X of Y") are driven by
one flag, ``EngineConfig.page_decorations``.  When it is off the frame uses the
full printable area, exactly like the reference report.
"""

from __future__ import annotations

from typing import Any

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

from ..config import EngineConfig, Theme


def make_numbered_canvas(theme: Theme, config: EngineConfig) -> type[Canvas]:
    """Canvas class that defers page output so it can print the total page count."""

    g, p, f = theme.geometry, theme.palette, theme.font

    class NumberedCanvas(Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._saved_pages: list[dict] = []

        def showPage(self) -> None:  # noqa: N802 (ReportLab API)
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total = len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total: int) -> None:
            width, height = g.page_size
            left, right = g.margin_left, width - g.margin_right
            # Running header
            top = height - g.margin_top
            self.setFont(f.bold, theme.type.body)
            self.setFillColor(p.heading)
            self.drawString(left, top - 7, config.running_header_text)
            self.setStrokeColor(p.header_rule)
            self.setLineWidth(0.75)
            self.line(left, top - 10, right, top - 10)
            # Running footer + page number
            bottom = g.margin_bottom
            self.setStrokeColor(p.thin_rule)
            self.setLineWidth(0.5)
            self.line(left, bottom + 10, right, bottom + 10)
            self.setFont(f.regular, theme.type.body)
            self.setFillColor(p.label)
            self.drawString(left, bottom + 3, config.running_footer_text)
            self.drawRightString(right, bottom + 3, f"Page {self._pageNumber} of {total}")

    return NumberedCanvas


class ReportDocTemplate(BaseDocTemplate):
    """Single-frame A4 template configured from the theme."""

    def __init__(self, target: Any, theme: Theme, config: EngineConfig) -> None:
        g = theme.geometry
        self.theme = theme
        self.config = config
        super().__init__(
            target,
            pagesize=g.page_size,
            leftMargin=g.margin_left,
            rightMargin=g.margin_right,
            topMargin=g.margin_top,
            bottomMargin=g.margin_bottom,
            title=config.title,
            author=config.author,
            creator="befisc_reportforge",
            subject="Consumer Credit Information Report",
        )
        top_reserve = g.running_header_height if config.page_decorations else 0.0
        bottom_reserve = g.running_footer_height if config.page_decorations else 0.0
        frame = Frame(
            self.leftMargin,
            self.bottomMargin + bottom_reserve,
            self.width,
            self.height - top_reserve - bottom_reserve,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id="content",
        )
        self.frame_height = self.height - top_reserve - bottom_reserve
        self.addPageTemplates([PageTemplate(id="report", frames=[frame])])

    def canvas_class(self) -> type[Canvas]:
        if self.config.page_decorations:
            return make_numbered_canvas(self.theme, self.config)
        return Canvas

    def build_story(self, story: list) -> None:
        self.build(story, canvasmaker=self.canvas_class())
