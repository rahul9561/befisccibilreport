"""Text preparation for ReportLab paragraphs."""

from __future__ import annotations

import unicodedata
from xml.sax.saxutils import escape

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)


def clean(value: str) -> str:
    """Collapse whitespace runs and drop zero-width characters."""
    if not value:
        return ""
    return " ".join(value.translate(_ZERO_WIDTH).split())


def to_winansi(value: str) -> str:
    """Make ``value`` safe for ReportLab's built-in (cp1252) Type-1 fonts.

    Characters outside cp1252 are decomposed (e.g. accented forms) and anything
    still unencodable becomes ``?`` rather than rendering as a black box.
    """
    try:
        value.encode("cp1252")
        return value
    except UnicodeEncodeError:
        pass
    out = []
    for ch in value:
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch).encode("cp1252", "ignore").decode("cp1252")
            out.append(base or "?")
    return "".join(out)


def markup(value: str, *, builtin_font: bool) -> str:
    """Clean, encode-guard and XML-escape a value for a ``Paragraph``."""
    value = clean(value)
    if builtin_font:
        value = to_winansi(value)
    return escape(value)


def plain(value: str, *, builtin_font: bool) -> str:
    """Clean and encode-guard a value drawn directly with ``drawString``."""
    value = clean(value)
    return to_winansi(value) if builtin_font else value
