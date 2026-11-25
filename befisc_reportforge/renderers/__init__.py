"""Section renderers.  Importing this package registers every built-in section."""

from . import accounts, consumer, contacts, header, summary  # noqa: F401  (registration side effects)
from .base import RenderContext, available_sections, get_section, section

__all__ = ["RenderContext", "available_sections", "get_section", "section"]
