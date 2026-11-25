"""Command line: ``python -m befisc_reportforge INPUT.json OUTPUT.pdf [options]``."""

from __future__ import annotations

import argparse
import logging
import sys

from . import PDFEngine, __version__
from .exceptions import ReportForgeError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="befisc_reportforge", description="Generate a credit-report PDF from JSON.")
    ap.add_argument("input", help="input JSON file")
    ap.add_argument("output", help="output PDF file")
    ap.add_argument("--font", choices=["helvetica", "roboto"], default="helvetica", help="font family")
    ap.add_argument("--page-decorations", action="store_true",
                    help="add running header/footer and page numbers")
    ap.add_argument("--template", default="cibil_cir", help="report template name")
    ap.add_argument("--logo", help="logo file (SVG/PNG/JPG); default assets/logo.svg")
    ap.add_argument("--strict", action="store_true", help="treat input warnings as errors")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        engine = PDFEngine(template=args.template, font_family=args.font,
                           page_decorations=args.page_decorations, strict=args.strict,
                           **({"logo_path": args.logo} if args.logo else {}))
        report = engine.generate(args.input, args.output)
    except ReportForgeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.output}: {len(report.accounts)} accounts, {len(report.enquiries)} enquiries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
