"""befisc_reportforge - JSON-driven PDF generation for bureau credit reports.

Quick start::

    from befisc_reportforge import PDFEngine

    engine = PDFEngine()                       # Helvetica, no page decorations
    engine.generate("input/sample.json", "output/report.pdf")

    PDFEngine(font_family="roboto", page_decorations=True).render_bytes(data)
"""

from __future__ import annotations

import logging

from .config import EngineConfig, Theme
from .engine import PDFEngine, generate_pdf
from .exceptions import (
    AssetError, InputError, RenderError, ReportForgeError, TemplateError, ValidationError,
)
from .layouts import ReportTemplate, available_templates, register_template
from .models import CreditReport
from .parser import parse_report
from .renderers import available_sections, section

__version__ = "1.0.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "AssetError", "CreditReport", "EngineConfig", "InputError", "PDFEngine", "RenderError",
    "ReportForgeError", "ReportTemplate", "TemplateError", "Theme", "ValidationError",
    "__version__", "available_sections", "available_templates", "generate_pdf", "parse_report",
    "register_template", "section",
]
