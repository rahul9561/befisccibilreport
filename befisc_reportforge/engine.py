"""Public engine: JSON in, PDF out.

    from befisc_reportforge import PDFEngine
    PDFEngine().generate("input/sample.json", "output/report.pdf")

Inputs may be a path, a JSON string, bytes, a file object or an already
loaded ``dict``.  Output may be a path, a binary file object, or omitted
(``render_bytes``) for web responses.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import IO, Any, Optional, Union

from reportlab.platypus.doctemplate import LayoutError

from .config import EngineConfig
from .exceptions import InputError, RenderError, ReportForgeError, ValidationError
from .fonts import register_family
from .layouts import ReportDocTemplate, get_template
from .models import CreditReport
from .renderers import RenderContext, get_section

log = logging.getLogger(__name__)

JsonSource = Union[str, os.PathLike, bytes, bytearray, dict, IO]


class PDFEngine:
    """Reusable, thread-safe JSON-to-PDF engine.

    One instance can serve many requests; it holds only configuration.
    """

    def __init__(self, config: Optional[EngineConfig] = None, **options: Any) -> None:
        base = config or EngineConfig()
        self.config = base.with_options(**options) if options else base
        self.theme = self.config.build_theme()
        self.template = get_template(self.config.template)
        register_family(self.theme.font, self.config.assets_dir)

    # ------------------------------------------------------------------ input
    @staticmethod
    def load_json(source: JsonSource) -> Any:
        """Load JSON from a path, string, bytes, file object or dict."""
        if isinstance(source, dict):
            return source
        try:
            if isinstance(source, (bytes, bytearray)):
                return json.loads(source.decode("utf-8-sig"))
            if hasattr(source, "read"):
                data = source.read()
                if isinstance(data, bytes):
                    data = data.decode("utf-8-sig")
                return json.loads(data)
            if isinstance(source, os.PathLike) or (
                isinstance(source, str) and not source.lstrip().startswith(("{", "["))
            ):
                path = Path(source)
                if not path.is_file():
                    raise InputError(f"Input JSON file not found: {path}")
                return json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(source, str):
                return json.loads(source)
        except json.JSONDecodeError as exc:
            raise InputError(f"Invalid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}") from exc
        except UnicodeDecodeError as exc:
            raise InputError(f"Input is not UTF-8 text: {exc}") from exc
        raise InputError(f"Unsupported input type: {type(source).__name__}")

    def parse(self, source: JsonSource) -> CreditReport:
        document = self.load_json(source)
        report = self.template.parser(document, use_raw_bureau_data=self.config.use_raw_bureau_data)
        if self.config.strict and report.warnings:
            raise ValidationError("Input has warnings and strict mode is on", report.warnings)
        return report

    # ------------------------------------------------------------------ output
    def build_story(self, report: CreditReport, frame_width: float, frame_height: float) -> list:
        ctx = RenderContext(self.theme, self.config, frame_width, frame_height)
        story: list = []
        for name in self.template.sections:
            story.extend(get_section(name)(report, ctx))
        return story

    def render(self, report: CreditReport, target: Union[str, os.PathLike, IO[bytes]]) -> None:
        doc = ReportDocTemplate(target, self.theme, self.config)
        story = self.build_story(report, doc.width, doc.frame_height)
        try:
            doc.build_story(story)
        except LayoutError as exc:
            raise RenderError(f"Content does not fit the page layout: {exc}") from exc

    def render_bytes(self, source: JsonSource) -> bytes:
        """Generate the PDF in memory (ideal for HTTP responses)."""
        report = self.parse(source)
        buf = io.BytesIO()
        self.render(report, buf)
        return buf.getvalue()

    def generate(self, input_json: JsonSource, output_pdf: Union[str, os.PathLike, IO[bytes]]) -> CreditReport:
        """Parse ``input_json`` and write the PDF to ``output_pdf``.

        Paths are written atomically (temp file + rename) so a failed run never
        leaves a truncated PDF behind.  Returns the parsed report.
        """
        report = self.parse(input_json)
        if hasattr(output_pdf, "write"):
            self.render(report, output_pdf)
            return report

        out = Path(output_pdf)
        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=".pdf", dir=out.parent)
        os.close(fd)
        try:
            self.render(report, tmp)
            os.replace(tmp, out)
        except ReportForgeError:
            raise
        except PermissionError as exc:
            raise RenderError(f"Cannot write {out}: {exc}") from exc
        except Exception as exc:
            log.exception("PDF generation failed")
            raise RenderError(f"PDF generation failed: {exc}") from exc
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        log.info("wrote %s (%d accounts, %d enquiries)", out, len(report.accounts), len(report.enquiries))
        return report


def generate_pdf(input_json: JsonSource, output_pdf: Union[str, os.PathLike, IO[bytes]], **options: Any) -> CreditReport:
    """One-shot helper: ``generate_pdf("in.json", "out.pdf", font_family="roboto")``."""
    return PDFEngine(**options).generate(input_json, output_pdf)
