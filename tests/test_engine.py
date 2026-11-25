"""End-to-end generation, input types, options and error handling."""

import io
import json

import pytest

from befisc_reportforge import (
    AssetError, EngineConfig, InputError, PDFEngine, TemplateError, ValidationError, generate_pdf,
)
from conftest import SAMPLE_JSON, page_count, pdf_text, truelink


@pytest.fixture(scope="module")
def engine():
    return PDFEngine()


def test_generate_to_path(tmp_path, engine):
    out = tmp_path / "nested" / "report.pdf"
    report = engine.generate(SAMPLE_JSON, out)
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and page_count(data) == 3
    assert len(report.accounts) == 10
    assert not list(out.parent.glob("*.pdf.tmp")) and len(list(out.parent.iterdir())) == 1  # atomic write


def test_every_section_is_rendered(engine, sample_doc):
    text = "\n".join(pdf_text(engine.render_bytes(sample_doc)))
    for heading in ["CONSUMER CIR", "CONSUMER INFORMATION:", "CIBIL TRANSUNION SCORE(S):", "IDENTIFICATION(S):",
                    "TELEPHONE(S):", "EMAIL CONTACT(S):", "ADDRESS(ES):", "EMPLOYMENT INFORMATION:",
                    "SUMMARY:", "ACCOUNT(S):", "ENQUIRIES:", "TransUnion CIBIL CIN"]:
        assert heading in text, heading
    assert "ANAND VARDHAN GOYAL S/O RAM GOPAL" in text and "837" in text
    assert "TOTAL: 10" in text and "ZERO-BALANCE: 9" in text
    assert "Page 1 of" not in text                        # decorations off by default


@pytest.mark.parametrize("kind", ["dict", "str", "bytes", "file", "path"])
def test_input_types(engine, sample_doc, kind):
    raw = json.dumps(sample_doc)
    source = {"dict": sample_doc, "str": raw, "bytes": raw.encode(), "file": io.StringIO(raw),
              "path": str(SAMPLE_JSON)}[kind]
    assert engine.render_bytes(source).startswith(b"%PDF")


def test_output_to_stream(engine, sample_doc):
    buf = io.BytesIO()
    engine.generate(sample_doc, buf)
    assert buf.getvalue().startswith(b"%PDF")


def test_page_decorations_flag(sample_doc):
    pages = pdf_text(PDFEngine(page_decorations=True).render_bytes(sample_doc))
    n = len(pages)
    for i, text in enumerate(pages, start=1):
        assert f"Page {i} of {n}" in text
        assert "TransUnion CIBIL - Consumer Credit Information Report" in text


def test_roboto_switch(sample_doc):
    import pymupdf

    data = PDFEngine(font_family="roboto").render_bytes(sample_doc)
    with pymupdf.open(stream=data, filetype="pdf") as d:
        fonts = {s["font"] for p in d for b in p.get_text("dict")["blocks"]
                 for ln in b.get("lines", []) for s in ln["spans"]}
    assert fonts and all(f.startswith("Roboto") for f in fonts)


def test_default_font_is_helvetica(sample_doc):
    import pymupdf

    data = PDFEngine().render_bytes(sample_doc)
    with pymupdf.open(stream=data, filetype="pdf") as d:
        fonts = {s["font"] for p in d for b in p.get_text("dict")["blocks"]
                 for ln in b.get("lines", []) for s in ln["spans"]}
    assert fonts == {"Helvetica", "Helvetica-Bold", "Helvetica-Oblique"}


def test_config_object_and_helper(tmp_path):
    cfg = EngineConfig(font_family="roboto", page_decorations=True)
    assert PDFEngine(cfg).config.page_decorations
    generate_pdf(SAMPLE_JSON, tmp_path / "x.pdf", font_family="helvetica")
    assert (tmp_path / "x.pdf").stat().st_size > 1000


def test_cli(tmp_path):
    from befisc_reportforge.__main__ import main

    out = tmp_path / "cli.pdf"
    assert main([str(SAMPLE_JSON), str(out), "--page-decorations"]) == 0 and out.exists()
    assert main([str(tmp_path / "missing.json"), str(out)]) == 1


# ---------------------------------------------------------------- errors

def test_unknown_font_and_template():
    with pytest.raises(AssetError):
        PDFEngine(font_family="comic-sans")
    with pytest.raises(TemplateError):
        PDFEngine(template="nope")


@pytest.mark.parametrize("bad, exc", [
    ("{not json", InputError),
    ("[]", ValidationError),
    ('{"hello": 1}', ValidationError),
    ('{"success": false, "message": "bureau down"}', ValidationError),
    ('{"TrueLinkCreditReport": {"Borrower": "oops"}}', ValidationError),
    (b"\xff\xfe\x00", InputError),
])
def test_bad_inputs_raise_clear_errors(engine, bad, exc):
    with pytest.raises(exc):
        engine.render_bytes(bad)


def test_missing_input_file(engine, tmp_path):
    with pytest.raises(InputError, match="not found"):
        engine.generate(tmp_path / "nope.json", tmp_path / "out.pdf")
    assert not (tmp_path / "out.pdf").exists()


def test_strict_mode_turns_warnings_into_errors(sample):
    del truelink(sample)["InquiryPartition"]
    PDFEngine().render_bytes(sample)                       # lenient: renders
    with pytest.raises(ValidationError, match="enquiries"):
        PDFEngine(strict=True).render_bytes(sample)


def test_logo_variants(tmp_path, sample_doc):
    from PIL import Image

    png, jpg = tmp_path / "logo.png", tmp_path / "logo.jpg"
    Image.new("RGB", (400, 100), (0, 166, 202)).save(png)
    Image.new("RGB", (400, 100), (0, 166, 202)).save(jpg)
    for logo in (png, jpg):
        assert PDFEngine(logo_path=logo).render_bytes(sample_doc).startswith(b"%PDF")
    # missing logo: skipped with a warning in lenient mode, error in strict mode
    report = PDFEngine(logo_path=tmp_path / "missing.svg").parse(sample_doc)
    PDFEngine(logo_path=tmp_path / "missing.svg").render(report, io.BytesIO())
    assert any("logo skipped" in w for w in report.warnings)
    with pytest.raises(AssetError):
        PDFEngine(logo_path=tmp_path / "missing.svg", strict=True).render_bytes(sample_doc)
