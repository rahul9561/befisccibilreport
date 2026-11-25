"""Visual regression against the supplied reference PDF.

``tests/fixtures/reference_consumer.json`` carries the same data as
``sample/report.pdf`` (built by ``tools/build_reference_fixture.py``), so the
generated PDF can be compared span by span.
"""

from collections import defaultdict

import pymupdf
import pytest

from befisc_reportforge import PDFEngine
from conftest import REFERENCE_JSON, REFERENCE_PDF

# Intentional difference: the reference adds four -1 sentinels into the overdue total.
KNOWN_DIFFERENCES = {"227546"}


def _spans(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                t = s["text"].replace("​", "").strip()
                if t:
                    out.append((t, s["origin"][0], s["origin"][1], round(s["size"], 1), s["color"],
                                "Bold" in s["font"], "Italic" in s["font"] or "Oblique" in s["font"]))
    return out


@pytest.fixture(scope="module")
def pair():
    data = PDFEngine().render_bytes(REFERENCE_JSON)
    ref = pymupdf.open(REFERENCE_PDF)
    gen = pymupdf.open(stream=data, filetype="pdf")
    yield ref, gen
    ref.close()
    gen.close()


def test_same_page_count(pair):
    ref, gen = pair
    assert gen.page_count == ref.page_count == 3


@pytest.mark.parametrize("pno", [0, 1, 2])
def test_spans_match_reference(pair, pno):
    ref, gen = pair
    by_text = defaultdict(list)
    for s in _spans(gen[pno]):
        by_text[s[0]].append(s)
    deltas, missing, styles = [], [], []
    for s in _spans(ref[pno]):
        if s[0] in KNOWN_DIFFERENCES:
            continue
        cands = by_text.get(s[0])
        if not cands:
            missing.append(s[0])
            continue
        best = min(cands, key=lambda c: abs(c[1] - s[1]) + abs(c[2] - s[2]))
        deltas.append((abs(best[1] - s[1]), abs(best[2] - s[2])))
        if best[3:] != s[3:]:
            styles.append((s[0], s[3:], best[3:]))
    assert not missing, f"text missing on page {pno + 1}: {missing[:10]}"
    assert not styles, f"font size/colour/weight differs: {styles[:5]}"
    max_dx = max(d[0] for d in deltas)
    max_dy = max(d[1] for d in deltas)
    mean = sum(d[0] + d[1] for d in deltas) / len(deltas)
    # Residual x offsets come only from kerning (Typst kerns, built-in Helvetica does not).
    assert max_dx <= 2.0 and max_dy <= 1.0 and mean <= 0.6, (max_dx, max_dy, mean)
