# befisc_reportforge

A JSON-to-PDF engine for **TransUnion CIBIL consumer credit reports (CIR)**.
It reads TrueLink JSON from the bureau and writes an A4 PDF that matches the
reference design in `sample/report.pdf`: the same layout, typography, colours,
tables, payment-history grids and pagination.

```python
from befisc_reportforge import PDFEngine

PDFEngine().generate("input/sample.json", "output/report.pdf")
```

---

## Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Configuration](#configuration)
5. [Input data and mapping rules](#input-data-and-mapping-rules)
6. [Architecture](#architecture)
7. [Extending the engine](#extending-the-engine)
8. [Django integration](#django-integration)
9. [Testing and visual verification](#testing-and-visual-verification)
10. [Known differences from the reference PDF](#known-differences-from-the-reference-pdf)
11. [Troubleshooting](#troubleshooting)

---

## Features

- **Matches the reference design.** All geometry was measured from
  `sample/report.pdf`. Compared span by span, the output is on average
  0.2–0.45 pt from the reference, with identical fonts, sizes, weights and
  colours.
- **No hardcoded report data.** Every value comes from the input JSON. Code
  tables translate CIBIL codes such as account type, ownership, collateral and
  enquiry purpose.
- **Accepts different input shapes.**
  - The full API envelope, a partial envelope, or a bare `TrueLinkCreditReport`
    object.
  - A single object where a list is expected.
  - Missing or `null` values anywhere.
- **Uses both data sources in the response.** The structured TrueLink report is
  the primary source. The raw bureau segment (`OriginalData`, base64) fills
  gaps, such as the complete enquiry list.
- **Calculated summary.**
  - Account totals, overdue and zero-balance counts.
  - High-credit, current-balance and overdue totals.
  - Most recent and oldest open dates.
  - Enquiry counts for the past 30 days, 12 months and 24 months, measured from
    the report date.
- **Pagination.**
  - Section headings are never left alone at the bottom of a page.
  - Account blocks are never split across pages, as in the reference.
  - Long tables continue onto the next page with their column headings
    repeated.
  - No blank pages.
- **Text wrapping.** Long names, addresses and unbroken account numbers wrap
  inside their columns.
- **Fonts.** Helvetica is the default. It has the same character widths as the
  reference font, Liberation Sans. Roboto (bundled, embedded, full Unicode) is
  available with one switch.
- **Logos.** SVG (drawn as vector graphics), PNG or JPG.
- **Optional page decorations.** One flag turns on a running header, a running
  footer and "Page X of Y" numbering.
- **Clear errors.** A typed exception hierarchy, log output, atomic file writes
  and an optional strict mode.

## Installation

You need Python 3.10 or later.

```bash
cd befisccibilpdf
python -m venv .venv
.venv\Scripts\activate             # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt    # runtime + test dependencies
```

To install it as a package in another project:

```bash
pip install -e /path/to/befisccibilpdf          # editable; finds ./assets automatically
# or
pip install /path/to/befisccibilpdf             # regular install; see "Assets" below
```

The runtime dependencies are `reportlab`, `svglib` and `pillow`. The tests and
the comparison tools also need `pytest` and `pymupdf`.

**Assets.** The logo (`logo.svg`) and the four Roboto fonts are bundled
inside the package (`befisc_reportforge/assets/`), so every install method
(wheel, `pip install`, editable, Docker) has them with no extra setup. To use
your own files, put them in a folder with the same layout and set
`PDFEngine(assets_dir=...)` or `BEFISC_REPORTFORGE_ASSETS=/path/to/assets`. Any
file missing from that folder falls back to the bundled copy. To use a
different logo file, pass `logo_path=...`.

## Usage

### Python

```python
from befisc_reportforge import PDFEngine

engine = PDFEngine()                                   # reusable and thread-safe

# 1. file -> file (written atomically; returns the parsed report)
report = engine.generate("input/sample.json", "output/report.pdf")
print(report.account_summary.total, report.enquiry_summary.past_12_months)

# 2. any JSON source -> bytes (for HTTP responses, S3 uploads, e-mail ...)
pdf_bytes = engine.render_bytes(json_dict_or_str_or_bytes_or_path_or_file)

# 3. parse only (to inspect or validate data without rendering)
report = engine.parse("input/sample.json")

# 4. one-shot helper
from befisc_reportforge import generate_pdf
generate_pdf("input/sample.json", "output/report.pdf", font_family="roboto")
```

`generate()` and `render_bytes()` accept a file path, a `pathlib.Path`, a JSON
string, bytes, a text or binary file object, or a `dict`. The output can be a
path or any binary stream.

### Command line

```bash
python -m befisc_reportforge input/sample.json output/report.pdf
python -m befisc_reportforge input/sample.json output/report.pdf --font roboto --page-decorations -v
befisc-reportforge input/sample.json output/report.pdf          # once installed
```

| Option | Meaning |
|---|---|
| `--font {helvetica,roboto}` | Font family (default `helvetica`) |
| `--page-decorations` | Turn on the running header, running footer and page numbers |
| `--logo PATH` | Use a different SVG, PNG or JPG logo |
| `--template NAME` | Report template (default `cibil_cir`) |
| `--strict` | Treat input warnings (missing sections) as errors |
| `-v` | Log at INFO level |

The command exits with status 0 on success and 1 on an engine error. The error
message is printed to stderr.

## Configuration

Pass options as keyword arguments or as an `EngineConfig`:

```python
from befisc_reportforge import EngineConfig, PDFEngine

engine = PDFEngine(font_family="roboto", page_decorations=True)
engine = PDFEngine(EngineConfig(page_decorations=True, logo_path="branding/logo.png"))
```

| Option | Default | Description |
|---|---|---|
| `font_family` | `"helvetica"` | **Font switch.** `"helvetica"`: built-in, same widths as the reference. `"roboto"`: bundled TTF, embedded, full Unicode. |
| `page_decorations` | `False` | **One flag** that turns on a running header, a running footer and "Page X of Y". Off by default because the reference has none. |
| `template` | `"cibil_cir"` | Report template name (see `available_templates()`) |
| `assets_dir` | `None`: `$BEFISC_REPORTFORGE_ASSETS`, then the bundled assets | Folder to search first for the fonts and the logo |
| `logo_path` | `assets/logo.svg` | `.svg`, `.png`, `.jpg` or `.jpeg` |
| `running_header_text` | `"CONSUMER CIR"` | Text in the title bar and in the running header |
| `running_footer_text` | `"TransUnion CIBIL - Consumer Credit Information Report"` | Running-footer text |
| `title`, `author` | `"Consumer CIR"`, `"befisc_reportforge"` | PDF metadata |
| `strict` | `False` | Raise `ValidationError` on warnings (for example, no accounts) instead of rendering empty sections |
| `use_raw_bureau_data` | `True` | Use the decoded `OriginalData` segment to fill gaps |

All visual constants live in `befisc_reportforge/config.py`:

- `Palette`: colours.
- `Typography`: font sizes, line spacing and the gap between a label and its
  value.
- `Geometry`: page size, margins, spacing between sections and payment-history
  cell sizes.

To change the look, adjust these values. You don't need to touch the rendering
code.

## Input data and mapping rules

The engine finds the `TrueLinkCreditReport` object wherever it sits in the
input. Its location in `input/sample.json` is
`raw_response.result.cibilData.GetCustomerAssetsResponse.GetCustomerAssetsSuccess.Asset.TrueLinkCreditReport`.

| PDF section | Source (TrueLink first, raw `OriginalData` segment as fallback) |
|---|---|
| Header: date and time | `Asset.CreationDate`, else `Sources.Source.InquiryDate` |
| Header: control number | `ReferenceKey`, else raw `ecn` |
| Consumer | `Borrower.BorrowerName.Name`, `Birth`, `Gender` |
| Score | `Borrower.CreditScore` (`riskScore`, `scoreName`, `CreditScoreFactor[].FactorText`) |
| Identification | `Borrower.IdentifierPartition.Identifier[].ID`. PAN and UID are listed first. `TaxId` is shown as "INCOME TAX ID NUMBER (PAN)". |
| Telephone / Email | `BorrowerTelephone[]` (type code `01`→Mobile, `03`→Office…), `EmailAddress` |
| Address | `BorrowerAddress[]`: `Dwelling`→category, `Ownership`→residence code. Shown as `street, city,state, PIN`. |
| Employment | `Borrower.Employer` (account type, date, occupation, income indicators) |
| Accounts | `TradeLinePartition[].Tradeline` + `GrantedTrade`, matched to raw accounts by serial number |
| Payment history | `GrantedTrade.PayStatusHistory.MonthlyPayStatus`, newest first, at most 36 months, 21 cells per row |
| Enquiries | Raw `inquiry[]` list when it is more complete (TrueLink keeps only the latest five), sorted newest first |

**How empty values are shown.** The bureau uses `-1` for "not reported". The
engine shows each field the way the reference does:

| Shown as reported (including `-1`) | Blank when `-1` | Special |
|---|---|---|
| Amount overdue, interest rate (`-1.00`), high credit, credit limit, actual payment, current balance | EMI, repayment tenure, collateral value, cash limit, written-off amounts, settlement amount, enquiry amount | Account closed: `NA` when open. Suit filed: `-` when none. Payment-history status: zero-padded (`0`→`000`); text codes such as `STD`, `SUB` and `SMA` are kept; a missing value becomes `XXX`. |

**How the summary is calculated** (`befisc_reportforge/calculations.py`):

- **TOTAL** is the number of accounts. **OVERDUE** counts accounts with an
  amount overdue above 0. **ZERO-BALANCE** counts accounts with a current
  balance of exactly 0.
- **HIGH CR/SANC. AMT** is the sum of high-credit amounts. **CURRENT** is the
  sum of current balances; credit balances such as `-179` are included.
  **OVERDUE** (amount) is the sum of positive overdue amounts.
- `-1` means "not reported" and is never added to a total.
- **RECENT** and **OLDEST** are the latest and earliest open dates.
- Enquiry counts are measured back from the report date. The windows include
  their start date: on or after *report date − 30 days*, and on or after the
  same calendar day 12 or 24 months earlier.

## Architecture

```
befisccibilpdf/
├── befisc_reportforge/
│   ├── __init__.py          public API: PDFEngine, generate_pdf, EngineConfig, exceptions
│   ├── __main__.py          command-line interface
│   ├── engine.py            PDFEngine: load JSON → parse → build the page content → write (path/stream/bytes)
│   ├── parser.py            TrueLink (+ decoded OriginalData) → typed report model
│   ├── validators.py        structure checks; fatal errors vs. warnings; finds the report in any envelope
│   ├── models.py            dataclasses: CreditReport, Account, Enquiry, summaries …
│   ├── calculations.py      summary values and enquiry windows
│   ├── config.py            Theme (Palette, Typography, Geometry, FontFamily) + EngineConfig
│   ├── fonts.py             thread-safe TTF registration (Roboto)
│   ├── exceptions.py        ReportForgeError → InputError / ValidationError / AssetError / TemplateError / RenderError
│   ├── data/codes.py        CIBIL code tables + lookup()
│   ├── utils/               null-safe access (dig, as_list), dates, text cleaning and encoding
│   ├── components/          reusable ReportLab building blocks
│   │   ├── base.py          Run / Styler / wrap_runs (word-wrap of mixed fonts) / Block (top-down drawing)
│   │   ├── primitives.py    Logo (SVG/PNG/JPG), TitleBar, SectionTitle, SubHeading, FieldColumns, TextBlock, Rule
│   │   ├── panels.py        GridPanel, StripedRows, ZebraTable (all split across pages, headings repeated)
│   │   ├── score.py         ScorePanel, ScoreRangePanel
│   │   ├── account.py       AccountBlock (four columns + payment-history grid; kept whole on one page)
│   │   └── groups.py        HeadedGroup: keeps a heading with the first piece of its content
│   ├── renderers/           one function per section, registered by name with @section("…")
│   │   ├── header.py        logo, header
│   │   ├── consumer.py      consumer, score
│   │   ├── contacts.py      identification, telephone, email, address, employment
│   │   ├── summary.py       summary
│   │   └── accounts.py      accounts, enquiries, disclaimer
│   └── layouts/
│       ├── __init__.py      ReportTemplate registry; "cibil_cir" = parser + ordered list of sections
│       └── base.py          ReportDocTemplate (frame, margins, metadata) + numbered canvas for page decorations
├── assets/                  Montserrat / Poppins / Roboto fonts, logo.svg
├── input/sample.json        supplied input (unchanged)
├── sample/report.pdf        supplied reference PDF (unchanged)
├── output/                  generated PDFs
├── tests/                   pytest suite + fixtures (reference-data JSON, synthetic many-account JSON)
└── tools/                   build_reference_fixture.py, compare_pdfs.py, make_synthetic.py
```

**How a report is produced**

```
JSON source ──load_json──▶ dict ──validators──▶ TrueLinkCreditReport (+ warnings)
           ──parser──▶ CreditReport (display-ready strings + numbers/dates for calculations)
           ──calculations──▶ account and enquiry summaries
           ──template.sections → renderers──▶ list of flowables (components)
           ──ReportDocTemplate.build──▶ PDF (page breaks handled by the components' split())
```

**Design decisions**

- **ReportLab**: pure Python, so it runs on Windows, Linux and Docker without
  system libraries (WeasyPrint needs GTK/Pango). It gives exact control over
  positioning.
- **Components draw at measured positions** inside flowables. This reproduces
  the reference geometry exactly, while ReportLab still handles page flow. Each
  component works out its own height from its content, which gives
  variable row heights and no overlaps.
- **The parser outputs display-ready values.** Renderers contain only layout
  code, and mapping rules can be tested on their own.
- **Fixed template text** (the score-range explanation, the disclaimer) lives in
  the renderers. Report data comes only from the JSON.

## Extending the engine

**Add a section:**

```python
from befisc_reportforge import section
from befisc_reportforge.components import GridPanel, HeadedGroup, SectionTitle, Styler

@section("remarks")
def render_remarks(report, ctx):
    s = Styler(ctx.theme)
    rows = [[[[s.value(w)]]] for w in report.warnings]
    return [HeadedGroup([SectionTitle(ctx.theme, "REMARKS:")],
                        GridPanel(ctx.theme, ctx.cols(1), ["NOTE"], rows))]
```

**Add or customise a template** (a different section order, another bureau):

```python
from befisc_reportforge import PDFEngine, ReportTemplate, register_template
from befisc_reportforge.layouts import CIBIL_CIR

register_template(ReportTemplate(
    name="cibil_cir_compact",
    parser=CIBIL_CIR.parser,                      # or your own parser for another JSON format
    sections=tuple(s for s in CIBIL_CIR.sections if s != "employment") + ("remarks",),
))
PDFEngine(template="cibil_cir_compact").generate("in.json", "out.pdf")
```

To support another bureau, write a parser that returns a `CreditReport`, or
your own model with matching renderers, then register a template that uses it.

## Django integration

```python
# settings.py
BEFISC_REPORTFORGE = {"font_family": "helvetica", "page_decorations": False}
# Logo and fonts are bundled in the package; nothing else to configure.
# To use your own logo: BEFISC_REPORTFORGE = {"logo_path": BASE_DIR / "static/img/logo.svg"}
```

```python
# reports/pdf.py — create one engine per process and reuse it
from django.conf import settings
from befisc_reportforge import PDFEngine

engine = PDFEngine(**getattr(settings, "BEFISC_REPORTFORGE", {}))
```

### Using `HttpResponse` (bytes in memory)

```python
# reports/views.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from befisc_reportforge import InputError, ValidationError, ReportForgeError
from .pdf import engine

@require_POST
def cibil_pdf(request):
    try:
        pdf = engine.render_bytes(request.body)          # raw JSON body
    except (InputError, ValidationError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except ReportForgeError as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="cibil-report.pdf"'
    return response
```

### Using `FileResponse` (streaming a buffer or a stored file)

```python
import io
from django.http import FileResponse, Http404
from .models import BureauResponse            # your model storing the JSON (JSONField)
from .pdf import engine

def cibil_pdf_download(request, pk):
    try:
        record = BureauResponse.objects.get(pk=pk, owner=request.user)
    except BureauResponse.DoesNotExist:
        raise Http404
    buffer = io.BytesIO()
    engine.generate(record.payload, buffer)       # dict straight from the JSONField
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"cibil-{pk}.pdf",
                        content_type="application/pdf")
```

To save the PDF once and serve it later:

```python
from django.core.files.base import ContentFile
record.pdf_file.save(f"cibil-{record.pk}.pdf", ContentFile(engine.render_bytes(record.payload)))
return FileResponse(record.pdf_file.open("rb"), filename=record.pdf_file.name, content_type="application/pdf")
```

```python
# urls.py
urlpatterns = [
    path("reports/cibil/pdf/", views.cibil_pdf),
    path("reports/<int:pk>/pdf/", views.cibil_pdf_download),
]
```

**Notes for production**

- `PDFEngine` holds only configuration, so a single instance can be shared
  across threads and requests.
- A typical report renders in well under a second. For very large reports or
  batch jobs, run `engine.generate(...)` in Celery or RQ and store the result.
- Add `logging.getLogger("befisc_reportforge")` to your `LOGGING` settings to
  record input warnings, such as skipped logos or missing sections.

## Testing and visual verification

```bash
python -m pytest                     # 56 tests
```

| Test file | What it covers |
|---|---|
| `test_utils.py` | Null-safe access, date formats, code lookup, text wrapping, encoding guard |
| `test_parser.py` | Field mapping for the sample and for the reference-data fixture, including the summary values printed in `sample/report.pdf` |
| `test_calculations.py` | Summary rules, the `-1` sentinel, enquiry-window boundaries |
| `test_engine.py` | Input types, output streams, CLI, both config switches, logo variants, error types, strict mode |
| `test_edge_cases.py` | Missing and `null` fields, single objects instead of lists, corrupt `OriginalData`, long text inside the margins, Unicode, 60 accounts and 150 enquiries, no blank pages, no orphaned headings, payment history capped at 36 months |
| `test_reference_match.py` | Every text span of `sample/report.pdf` is found in the generated PDF with the same font, size and colour, within the position tolerance |

**Comparing against the reference.** The supplied `sample.json` and
`sample/report.pdf` belong to different consumers, so they can't be compared
directly.

- `tools/build_reference_fixture.py` rebuilds the reference consumer's data as
  TrueLink JSON in `tests/fixtures/reference_consumer.json`.
- `tools/compare_pdfs.py` then renders both PDFs to PNG and writes red/cyan
  overlay images. For every text span, it reports the position offset and any
  style difference:

```bash
python -m befisc_reportforge tests/fixtures/reference_consumer.json output/reference_consumer_report.pdf
python tools/compare_pdfs.py sample/report.pdf output/reference_consumer_report.pdf output/compare
```

Current result: 3 pages against 3, 1,206 of 1,207 spans matched, and no font,
size or colour differences. The average offset is 0.22, 0.44 and 0.30 pt on
pages 1–3, and the largest is 1.7 pt.

`tools/make_synthetic.py` creates a fictitious consumer with many accounts
(40 accounts and 60 enquiries by default) for pagination tests. Its output is
`tests/fixtures/synthetic_many_accounts.json`, which renders to 9 pages.

## Known differences from the reference PDF

1. **Kerning.** Typst, which produced the reference, applies kerning; ReportLab's
   built-in Helvetica does not. Some labels are therefore up to 1.7 pt wider,
   for example `CATEGORY:` is 36.0 pt here against 34.9 pt in the reference.
   Line breaks and layout are unaffected.
2. **Overdue amount in SUMMARY.** The reference shows `227546`, which is
   `227550 + 4 × (−1)`: it added the "not reported" markers. This engine leaves
   them out and shows `227550`.
3. **Logo.** The reference embeds a raster image of the logo. This engine draws
   `assets/logo.svg` as vector graphics in the same 200 × 53 pt box, so it stays
   sharp at any zoom level.
4. **Field names the sample JSON doesn't contain.** Credit-facility status,
   suit-filed status, member ID and member reference number are read from
   TrueLink (`CreditFacilityStatus`, `SuitFiledWilfulDefault`) or from the raw
   segment (`creditFacilityStatus`, `suitFiledWilfulDefault`, …). The supplied
   sample has none of these, so the field names are the standard TUEF and
   TrueLink names, not names confirmed against your real data.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AssetError: Font file … not found` | Reinstall the package (version 1.0.3 or later bundles the fonts), or fix your `assets_dir` |
| Logo missing, with "logo skipped" in the log | Versions before 1.0.3 looked for `<project>/assets`, which a wheel install doesn't have; upgrade. If you passed `logo_path`, check that the file exists. Use `strict=True` to make a missing logo an error. |
| `?` in place of non-Latin characters | Helvetica only covers Western European characters; use `font_family="roboto"` |
| `ValidationError: No credit report found` | The JSON has no `TrueLinkCreditReport` object; check the bureau response |
| `ValidationError: Bureau response is not successful` | The input has `"success": false`; the bureau call failed upstream |
