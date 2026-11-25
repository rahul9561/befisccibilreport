from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures"
SAMPLE_JSON = ROOT / "input" / "sample.json"
REFERENCE_PDF = ROOT / "sample" / "report.pdf"
REFERENCE_JSON = FIXTURES / "reference_consumer.json"


@pytest.fixture(scope="session")
def sample_doc() -> dict:
    return json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def reference_doc() -> dict:
    return json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))


@pytest.fixture
def sample(sample_doc) -> dict:
    """A mutable deep copy of the sample input."""
    return copy.deepcopy(sample_doc)


def truelink(doc: dict) -> dict:
    return doc["raw_response"]["result"]["cibilData"]["GetCustomerAssetsResponse"][
        "GetCustomerAssetsSuccess"]["Asset"]["TrueLinkCreditReport"]


def pdf_text(data: bytes) -> list[str]:
    with pymupdf.open(stream=data, filetype="pdf") as d:
        return [p.get_text() for p in d]


def page_count(data: bytes) -> int:
    with pymupdf.open(stream=data, filetype="pdf") as d:
        return d.page_count
