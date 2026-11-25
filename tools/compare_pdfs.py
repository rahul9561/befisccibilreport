"""Compare a generated PDF with the reference, page by page.

Reports, for every text span of the reference:
  * whether the same text exists on the same page of the generated PDF,
  * the baseline offset (dx, dy) of the closest match,
  * font style (regular/bold/italic), size and colour mismatches,
and renders PNGs plus a red/cyan overlay image per page.

Usage:
    python tools/compare_pdfs.py sample/report.pdf output/reference_consumer_report.pdf [out_dir]

Exit code 1 when any span is missing or off by more than --tolerance points.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf


def style(font: str) -> str:
    f = font.lower()
    bold = "bold" in f
    italic = "italic" in f or "oblique" in f
    return ("bold" if bold else "") + ("italic" if italic else "") or "regular"


def spans(page) -> list[dict]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for s in line["spans"]:
                t = s["text"].replace("​", "").strip()
                if t:
                    out.append({"text": t, "x": s["origin"][0], "y": s["origin"][1], "size": s["size"],
                                "style": style(s["font"]), "color": s["color"]})
    return out


def overlay(ref_png: Path, gen_png: Path, out_png: Path) -> float:
    """Reference in red, generated in cyan; returns % of differing pixels."""
    from PIL import Image, ImageChops

    a = Image.open(ref_png).convert("L")
    b = Image.open(gen_png).convert("L").resize(a.size)
    merged = Image.merge("RGB", (a, b, b))
    merged.save(out_png)
    diff = ImageChops.difference(a, b).point(lambda v: 255 if v > 64 else 0)
    hist = diff.histogram()
    return 100.0 * hist[255] / (a.size[0] * a.size[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("generated")
    ap.add_argument("out_dir", nargs="?", default="output/compare")
    ap.add_argument("--tolerance", type=float, default=1.0, help="max allowed offset in points")
    ap.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()

    ref, gen = pymupdf.open(args.reference), pymupdf.open(args.generated)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"pages: reference={ref.page_count} generated={gen.page_count}")
    failures = 0
    for pno in range(max(ref.page_count, gen.page_count)):
        if pno >= ref.page_count or pno >= gen.page_count:
            print(f"page {pno + 1}: present in only one document")
            failures += 1
            continue
        rp, gp = ref[pno], gen[pno]
        for tag, page in (("ref", rp), ("gen", gp)):
            page.get_pixmap(dpi=args.dpi).save(out / f"{tag}_p{pno + 1}.png")
        pct = overlay(out / f"ref_p{pno + 1}.png", out / f"gen_p{pno + 1}.png", out / f"overlay_p{pno + 1}.png")

        gen_by_text = defaultdict(list)
        for s in spans(gp):
            gen_by_text[s["text"]].append(s)
        missing, offsets, style_diff = [], [], []
        for s in spans(rp):
            cands = gen_by_text.get(s["text"])
            if not cands:
                missing.append(s)
                continue
            best = min(cands, key=lambda c: abs(c["x"] - s["x"]) + abs(c["y"] - s["y"]))
            dx, dy = best["x"] - s["x"], best["y"] - s["y"]
            offsets.append((abs(dx) + abs(dy), dx, dy, s["text"]))
            if (best["style"], round(best["size"], 1), best["color"]) != (s["style"], round(s["size"], 1), s["color"]):
                style_diff.append((s["text"], (s["style"], s["size"], hex(s["color"])),
                                   (best["style"], best["size"], hex(best["color"]))))
        bad = [o for o in offsets if abs(o[1]) > args.tolerance or abs(o[2]) > args.tolerance]
        mean = sum(o[0] for o in offsets) / len(offsets) if offsets else 0
        print(f"page {pno + 1}: spans matched={len(offsets)} missing={len(missing)} "
              f"off>{args.tolerance}pt={len(bad)} mean|d|={mean:.2f}pt style-diffs={len(style_diff)} "
              f"pixel-diff={pct:.2f}%")
        for o in sorted(bad, reverse=True)[:15]:
            print(f"    offset dx={o[1]:+.1f} dy={o[2]:+.1f}  {o[3][:70]!r}")
        for m in missing[:10]:
            print(f"    missing  {m['text'][:70]!r} at ({m['x']:.1f},{m['y']:.1f})")
        for sd in style_diff[:10]:
            print(f"    style    {sd[0][:40]!r} ref={sd[1]} gen={sd[2]}")
        failures += len(missing) + len(bad)
    print(f"images written to {out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
