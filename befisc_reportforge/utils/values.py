"""Null-safe access and value normalisation helpers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Iterator, Optional

# The bureau uses -1 as "not reported" for numeric fields.
SENTINEL = -1


def dig(obj: Any, *path: Any, default: Any = None) -> Any:
    """Walk ``path`` through nested dicts/lists, returning ``default`` on any miss.

    >>> dig({"a": [{"b": 1}]}, "a", 0, "b")
    1
    """
    cur = obj
    for key in path:
        if cur is None:
            return default
        if isinstance(key, int):
            if isinstance(cur, list) and -len(cur) <= key < len(cur):
                cur = cur[key]
            elif isinstance(cur, dict) and key == 0:
                # A single object where a list was expected.
                continue
            else:
                return default
        elif isinstance(cur, dict):
            if key not in cur:
                return default
            cur = cur[key]
        else:
            return default
    return default if cur is None else cur


def as_list(value: Any) -> list:
    """Bureau XML->JSON converters emit a dict for a single element; normalise to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None]
    return [value]


def text(value: Any) -> str:
    """String form of a scalar; ``None`` and containers become ``""``."""
    if value is None or isinstance(value, (dict, list)):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def symbol(node: Any) -> str:
    """Code of an enumerated bureau node ``{"symbol": .., "description": ..}``."""
    if isinstance(node, dict):
        return text(node.get("symbol"))
    return text(node)


def described(node: Any, table: Optional[dict] = None) -> str:
    """Human text for an enumerated node: its description, else the table lookup."""
    from ..data.codes import lookup

    if isinstance(node, dict):
        desc = text(node.get("description"))
        if desc:
            return desc
        code = text(node.get("symbol"))
    else:
        code = text(node)
    if table is None:
        return code
    return lookup(table, code)


def to_number(value: Any) -> Optional[Decimal]:
    """Parse a bureau numeric value; returns ``None`` for blanks or garbage."""
    raw = text(value).replace(",", "")
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def is_reported(value: Any) -> bool:
    """True when a numeric value is present and not the ``-1`` sentinel."""
    num = to_number(value)
    return num is not None and num != SENTINEL


def first_nonempty(*values: Any) -> str:
    for v in values:
        t = text(v)
        if t:
            return t
    return ""


def unique(items: Iterable[str]) -> Iterator[str]:
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            yield item
