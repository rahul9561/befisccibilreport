"""Section-renderer contract and registry.

A section renderer is a function ``(report, ctx) -> list[Flowable]``
registered under a name with :func:`section`.  Templates (see
:mod:`befisc_reportforge.layouts`) are ordered lists of section names, so new
report formats reuse existing sections and add only what differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from reportlab.platypus import Flowable

from ..config import EngineConfig, Theme
from ..exceptions import TemplateError
from ..models import CreditReport


@dataclass(frozen=True)
class RenderContext:
    theme: Theme
    config: EngineConfig
    frame_width: float
    frame_height: float

    def cols(self, n: int, reduce: float = 8.0, start: float = 4.0) -> list:
        """``n`` equal columns starting at ``start``, sharing ``frame_width - reduce``.

        The reference uses ``reduce=8`` (inset both sides) for identification /
        telephone panels and ``reduce=4`` for summary / employment panels.
        """
        from ..components import Column

        w = (self.frame_width - reduce) / n
        return [Column(start + i * w, w) for i in range(n)]


SectionFn = Callable[[CreditReport, RenderContext], list[Flowable]]
_REGISTRY: dict[str, SectionFn] = {}


def section(name: str) -> Callable[[SectionFn], SectionFn]:
    def deco(fn: SectionFn) -> SectionFn:
        if name in _REGISTRY and _REGISTRY[name] is not fn:
            raise TemplateError(f"section {name!r} registered twice")
        _REGISTRY[name] = fn
        return fn
    return deco


def get_section(name: str) -> SectionFn:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise TemplateError(f"unknown section {name!r}; available: {sorted(_REGISTRY)}") from None


def available_sections() -> list[str]:
    return sorted(_REGISTRY)
