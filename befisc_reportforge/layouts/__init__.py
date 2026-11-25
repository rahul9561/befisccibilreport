"""Report templates: an ordered list of sections plus a parser.

Add a template by calling :func:`register_template`; sections are looked up
in the renderer registry (:mod:`befisc_reportforge.renderers`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..exceptions import TemplateError
from ..models import CreditReport
from .base import ReportDocTemplate, make_numbered_canvas


@dataclass(frozen=True)
class ReportTemplate:
    name: str
    sections: tuple[str, ...]
    parser: Callable[..., CreditReport]
    description: str = ""


_TEMPLATES: dict[str, ReportTemplate] = {}


def register_template(template: ReportTemplate) -> ReportTemplate:
    _TEMPLATES[template.name] = template
    return template


def get_template(name: str) -> ReportTemplate:
    try:
        return _TEMPLATES[name]
    except KeyError:
        raise TemplateError(f"unknown template {name!r}; available: {sorted(_TEMPLATES)}") from None


def available_templates() -> list[str]:
    return sorted(_TEMPLATES)


def _cibil_parser(document: Any, **kwargs: Any) -> CreditReport:
    from ..parser import parse_report

    return parse_report(document, **kwargs)


CIBIL_CIR = register_template(ReportTemplate(
    name="cibil_cir",
    description="TransUnion CIBIL Consumer CIR (TrueLink JSON)",
    parser=_cibil_parser,
    sections=(
        "logo", "header", "consumer", "score", "identification", "telephone", "email",
        "address", "employment", "summary", "accounts", "enquiries", "disclaimer",
    ),
))

__all__ = [
    "CIBIL_CIR", "ReportDocTemplate", "ReportTemplate", "available_templates", "get_template",
    "make_numbered_canvas", "register_template",
]
