"""Structural validation of incoming bureau JSON.

Validation separates *fatal* problems (the report cannot be produced) from
*warnings* (sections will be empty).  Warnings are logged and attached to the
parsed report; ``EngineConfig.strict`` turns them into errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .exceptions import ValidationError

REPORT_KEY = "TrueLinkCreditReport"
_MAX_SEARCH_DEPTH = 12


@dataclass
class ValidationResult:
    report: dict
    path: str
    warnings: list[str] = field(default_factory=list)


def find_key(obj: Any, key: str, path: str = "$", depth: int = 0) -> Optional[tuple[Any, str]]:
    """Breadth-first search for ``key``; returns ``(value, json_path)``.

    Lets the engine accept the full API envelope, a partial envelope, or the
    bare ``TrueLinkCreditReport`` object interchangeably.
    """
    queue: list[tuple[Any, str, int]] = [(obj, path, depth)]
    while queue:
        node, p, d = queue.pop(0)
        if d > _MAX_SEARCH_DEPTH:
            continue
        if isinstance(node, dict):
            if key in node:
                return node[key], f"{p}.{key}"
            queue.extend((v, f"{p}.{k}", d + 1) for k, v in node.items() if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            queue.extend((v, f"{p}[{i}]", d + 1) for i, v in enumerate(node) if isinstance(v, (dict, list)))
    return None


def _looks_like_report(obj: Any) -> bool:
    return isinstance(obj, dict) and "Borrower" in obj and (
        "TradeLinePartition" in obj or "InquiryPartition" in obj or "ReferenceKey" in obj
    )


def validate_document(doc: Any) -> ValidationResult:
    if not isinstance(doc, dict):
        raise ValidationError(
            "Input JSON must be an object", [f"top-level value is {type(doc).__name__}"]
        )

    if doc.get("success") is False:
        msg = doc.get("message") or doc.get("error") or "bureau call reported success=false"
        raise ValidationError("Bureau response is not successful", [str(msg)])

    if _looks_like_report(doc):
        report, path = doc, "$"
    else:
        found = find_key(doc, REPORT_KEY)
        if found is None:
            raise ValidationError(
                "No credit report found in input",
                [f"expected a '{REPORT_KEY}' object (searched {_MAX_SEARCH_DEPTH} levels deep)"],
            )
        report, path = found

    problems: list[str] = []
    if isinstance(report, list):
        report = report[0] if report and isinstance(report[0], dict) else None
    if not isinstance(report, dict):
        raise ValidationError("Credit report has the wrong type", [f"{path} is not an object"])

    borrower = report.get("Borrower")
    if isinstance(borrower, list):
        borrower = borrower[0] if borrower else None
        report = {**report, "Borrower": borrower}
    if not isinstance(borrower, dict):
        problems.append(f"{path}.Borrower is missing or not an object")

    for key in ("TradeLinePartition", "InquiryPartition"):
        val = report.get(key)
        if val is not None and not isinstance(val, (list, dict)):
            problems.append(f"{path}.{key} must be a list or object, got {type(val).__name__}")

    if problems:
        raise ValidationError("Credit report structure is invalid", problems)

    warnings: list[str] = []
    if not report.get("TradeLinePartition"):
        warnings.append("no accounts (TradeLinePartition) in report")
    if not report.get("InquiryPartition"):
        warnings.append("no enquiries (InquiryPartition) in report")
    if not borrower.get("CreditScore"):
        warnings.append("no CreditScore in report")
    if not report.get("ReferenceKey"):
        warnings.append("no ReferenceKey (control number) in report")
    return ValidationResult(report=report, path=path, warnings=warnings)
