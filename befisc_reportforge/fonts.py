"""Font registration.

Helvetica is one of ReportLab's 14 built-in fonts and needs no files.  Any
TTF-based family (Roboto) is registered once per process from the assets
directory and embedded (subset) into the PDF.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont

from .config import FontFamily
from .exceptions import AssetError

log = logging.getLogger(__name__)
_lock = threading.Lock()
_registered: set[str] = set()


def register_family(family: FontFamily, assets_dir: Path) -> None:
    """Register ``family``'s TTF files (idempotent and thread-safe)."""
    if family.is_builtin:
        return
    with _lock:
        if family.name in _registered:
            return
        for font_name, rel in family.files:
            path = Path(assets_dir) / rel
            if not path.is_file():
                raise AssetError(f"Font file for {font_name!r} not found: {path}")
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
            except TTFError as exc:
                raise AssetError(f"Font file {path} could not be loaded: {exc}") from exc
        addMapping(family.regular, 0, 0, family.regular)
        addMapping(family.regular, 1, 0, family.bold)
        addMapping(family.regular, 0, 1, family.italic)
        addMapping(family.regular, 1, 1, family.bold_italic)
        _registered.add(family.name)
        log.debug("registered font family %s", family.name)
