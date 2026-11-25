"""Missing fields, nulls, long text, many records and pagination."""

import pymupdf
import pytest

from befisc_reportforge import PDFEngine, parse_report
from conftest import page_count, pdf_text, truelink
from tools.make_synthetic import build as build_synthetic


@pytest.fixture(scope="module")
def engine():
    return PDFEngine()


def assert_valid_pdf(data: bytes) -> list[str]:
    assert data.startswith(b"%PDF")
    pages = pdf_text(data)
    # No blank pages: every page carries text.
    assert all(p.strip() for p in pages), "blank page produced"
    return pages


def test_minimal_report(engine):
    doc = {"TrueLinkCreditReport": {"Borrower": {}}}
    pages = assert_valid_pdf(engine.render_bytes(doc))
    assert len(pages) == 1
    text = pages[0]
    assert "No accounts reported" in text and "No addresses reported" in text
    assert "TOTAL: 0" in text


def test_nulls_everywhere(engine, sample):
    t = truelink(sample)
    b = t["Borrower"]
    b["BorrowerName"] = None
    b["Birth"] = None
    b["Gender"] = None
    b["CreditScore"] = None
    b["EmailAddress"] = None
    b["BorrowerTelephone"] = [None, {"PhoneNumber": None, "PhoneType": None}]
    b["IdentifierPartition"] = {"Identifier": None}
    for part in t["TradeLinePartition"]:
        tl = part["Tradeline"]
        for k in list(tl):
            tl[k] = None
    t["InquiryPartition"] = None
    t["Sources"] = None                                    # also disables raw-bureau fallback
    report = parse_report(sample)
    assert report.consumer.name == "" and report.scores == [] and report.emails == []
    assert len(report.accounts) == 10
    assert all(a.account_closed == "NA" for a in report.accounts)
    assert_valid_pdf(engine.render_bytes(sample))


def test_single_objects_instead_of_lists(engine, sample):
    t = truelink(sample)
    t["TradeLinePartition"] = t["TradeLinePartition"][0]
    t["InquiryPartition"] = t["InquiryPartition"][0]
    t["Borrower"]["BorrowerAddress"] = t["Borrower"]["BorrowerAddress"][0]
    r = parse_report(sample, use_raw_bureau_data=False)
    assert (len(r.accounts), len(r.enquiries), len(r.addresses)) == (1, 1, 1)
    assert_valid_pdf(engine.render_bytes(sample))


def test_corrupt_original_data_is_ignored(engine, sample):
    truelink(sample)["Sources"]["Source"]["OriginalData"] = "@@not-base64@@"
    r = parse_report(sample)
    assert len(r.enquiries) == 5                           # falls back to TrueLink list
    assert_valid_pdf(engine.render_bytes(sample))


def test_long_text_wraps_without_overflow(engine, sample):
    t = truelink(sample)
    long_name = "VERYLONGCONSUMERNAMEWITHOUTSPACES" * 4 + " AND MORE WORDS " * 6
    t["Borrower"]["BorrowerName"]["Name"]["Forename"] = long_name
    t["Borrower"]["BorrowerAddress"][0]["CreditAddress"]["StreetAddress"] = "LONG ADDRESS SEGMENT " * 30
    t["TradeLinePartition"][0]["Tradeline"]["creditorName"] = "A VERY LONG LENDER NAME " * 6
    t["TradeLinePartition"][0]["Tradeline"]["accountNumber"] = "9" * 80
    data = engine.render_bytes(sample)
    assert_valid_pdf(data)
    with pymupdf.open(stream=data, filetype="pdf") as d:
        for page in d:
            for b in page.get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    for s in ln["spans"]:
                        x0, _, x1, _ = s["bbox"]
                        baseline = s["origin"][1]
                        # Text stays inside the 19 pt margins (glyph boxes include
                        # side bearings, hence the 0.5 pt allowance).
                        assert x0 >= 18.5 and x1 <= page.rect.width - 18.5, (s["text"], x0, x1)
                        assert 19 + s["size"] * 0.7 <= baseline <= page.rect.height - 19, (s["text"], baseline)


def test_unicode_with_builtin_and_ttf_fonts(sample):
    truelink(sample)["Borrower"]["BorrowerName"]["Name"]["Forename"] = "JOSÉ ÅNGSTRÖM नमस्ते"
    text = "".join(pdf_text(PDFEngine().render_bytes(sample)))
    assert "JOSÉ ÅNGSTRÖM" in text                         # cp1252 chars kept, others replaced
    assert_valid_pdf(PDFEngine(font_family="roboto").render_bytes(sample))


def test_many_accounts_paginate_cleanly(engine):
    doc = build_synthetic(n_accounts=60, n_enquiries=150, seed=3)
    data = engine.render_bytes(doc)
    pages = assert_valid_pdf(data)
    assert len(pages) >= 10
    text = "\n".join(pages)
    assert text.count("MEMBER NAME:") == 60
    assert "TOTAL: 60" in text
    # Each account block stays on one page: its header and DPD title share a page.
    for page in pages:
        assert page.count("MEMBER NAME:") == page.count("DAYS PAST DUE/ASSET CLASSIFICATION")
    # Enquiry table continues across pages with its header repeated.
    assert sum("ENQUIRY AMOUNT" in p for p in pages) >= 2
    assert text.count("ENQUIRIES:") == 1


def test_no_orphaned_section_headings(engine):
    """A section title is never the last thing on a page."""
    data = engine.render_bytes(build_synthetic(n_accounts=25, n_enquiries=80, seed=11))
    headings = ("ACCOUNT(S):", "ENQUIRIES:", "SUMMARY:", "ADDRESS(ES):")
    with pymupdf.open(stream=data, filetype="pdf") as d:
        for page in d:
            words = [w for w in page.get_text("words")]
            if not words:
                continue
            last_line_y = max(w[3] for w in words)
            last_text = " ".join(w[4] for w in words if abs(w[3] - last_line_y) < 1)
            assert last_text not in headings, f"orphaned heading on page {page.number + 1}"


def test_payment_history_capped_at_36(engine, sample):
    gt = truelink(sample)["TradeLinePartition"][-1]["Tradeline"]["GrantedTrade"]
    hist = gt["PayStatusHistory"]["MonthlyPayStatus"]
    for i in range(37, 61):
        hist[str(i)] = {"date": "2020-01-01+05:30", "status": "0"}
    r = parse_report(sample)
    assert len(r.accounts[-1].payment_history) == 36


def test_dpd_status_normalisation(sample):
    gt = truelink(sample)["TradeLinePartition"][-1]["Tradeline"]["GrantedTrade"]
    hist = gt["PayStatusHistory"]["MonthlyPayStatus"]
    hist["1"]["status"], hist["2"]["status"], hist["3"]["status"], hist["4"]["status"] = "5", "std", "", "-1"
    statuses = [p.status for p in parse_report(sample).accounts[-1].payment_history[:4]]
    assert statuses == ["005", "STD", "XXX", "XXX"]


def test_synthetic_fixture_renders(engine):
    from conftest import FIXTURES

    data = engine.render_bytes(FIXTURES / "synthetic_many_accounts.json")
    pages = assert_valid_pdf(data)
    assert page_count(data) == len(pages) >= 8
    assert "PRIYA RAMESH KULKARNI-DESHPANDE" in pages[0]
