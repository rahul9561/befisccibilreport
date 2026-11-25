"""Configuration: theme (colours, typography, geometry) and engine options.

Every visual constant used by the components lives here so a deployment can
re-skin the report without touching rendering code.  Defaults reproduce the
reference CIBIL CIR PDF (A4, 19 pt margins, Arial-metric font at 6.5 pt).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
# Fonts/logo location: $BEFISC_REPORTFORGE_ASSETS, else <project>/assets.
DEFAULT_ASSETS_DIR = Path(os.environ.get("BEFISC_REPORTFORGE_ASSETS", PROJECT_DIR / "assets"))


@dataclass(frozen=True)
class FontFamily:
    """Logical font family: ReportLab font names for each style."""

    name: str
    regular: str
    bold: str
    italic: str
    bold_italic: str
    # TTF files to register ({reportlab_name: relative path under assets/}).
    # Empty for ReportLab's built-in Type-1 fonts.
    files: tuple[tuple[str, str], ...] = ()

    @property
    def is_builtin(self) -> bool:
        return not self.files


HELVETICA = FontFamily(
    name="helvetica",
    regular="Helvetica",
    bold="Helvetica-Bold",
    italic="Helvetica-Oblique",
    bold_italic="Helvetica-BoldOblique",
)

ROBOTO = FontFamily(
    name="roboto",
    regular="BRF-Roboto",
    bold="BRF-Roboto-Bold",
    italic="BRF-Roboto-Italic",
    bold_italic="BRF-Roboto-BoldItalic",
    files=(
        ("BRF-Roboto", "Roboto/static/Roboto-Regular.ttf"),
        ("BRF-Roboto-Bold", "Roboto/static/Roboto-Bold.ttf"),
        ("BRF-Roboto-Italic", "Roboto/static/Roboto-Italic.ttf"),
        ("BRF-Roboto-BoldItalic", "Roboto/static/Roboto-BoldItalic.ttf"),
    ),
)

FONT_FAMILIES: dict[str, FontFamily] = {f.name: f for f in (HELVETICA, ROBOTO)}


@dataclass(frozen=True)
class Palette:
    text: Color = HexColor("#000000")
    label: Color = HexColor("#808080")          # italic field labels
    heading: Color = HexColor("#656565")        # section titles
    column_header: Color = HexColor("#00A7D4")  # cyan column headings
    accent_dark: Color = HexColor("#00678E")    # score / score name
    alert: Color = HexColor("#D84042")          # score-range values
    title_bar: Color = HexColor("#FAD700")      # yellow "CONSUMER CIR" bar
    header_rule: Color = HexColor("#00A7D4")
    footer_rule: Color = HexColor("#00A6C9")
    thin_rule: Color = HexColor("#878787")
    panel: Color = HexColor("#EDEDED")
    stripe: Color = HexColor("#F0F0F0")
    white: Color = HexColor("#FFFFFF")


@dataclass(frozen=True)
class Typography:
    body: float = 6.5
    column_header: float = 6.0
    sub_heading: float = 7.0
    section_title: float = 8.0
    title_bar: float = 10.0
    score: float = 16.0
    leading: float = 7.47        # baseline-to-baseline for 6.5 pt rows
    header_leading: float = 6.5  # wrapped column headings
    label_gap: float = 2.9       # gap between "LABEL:" and its value


@dataclass(frozen=True)
class Geometry:
    page_size: tuple[float, float] = A4
    margin_left: float = 19.0
    margin_right: float = 19.0
    margin_top: float = 19.0
    margin_bottom: float = 19.0
    logo_width: float = 200.0
    logo_gap: float = 9.3           # logo bottom -> title bar top
    section_gap: float = 14.5       # previous block bottom -> section title baseline
    title_to_panel: float = 5.0     # section title baseline -> panel top
    panel_header_offset: float = 8.1  # panel top -> first (header) baseline
    panel_bottom_pad: float = 4.0   # last baseline -> panel bottom
    cell_inset: float = 4.0         # text inset inside panels
    dpd_cell_width: float = 26.0
    dpd_row_pitch: float = 18.1
    dpd_cells_per_row: int = 21
    account_rule_width: float = 1.5
    account_gap: float = 5.2        # account rule bottom -> next block top
    running_header_height: float = 16.0
    running_footer_height: float = 16.0

    @property
    def content_width(self) -> float:
        return self.page_size[0] - self.margin_left - self.margin_right


@dataclass(frozen=True)
class Theme:
    font: FontFamily = HELVETICA
    palette: Palette = field(default_factory=Palette)
    type: Typography = field(default_factory=Typography)
    geometry: Geometry = field(default_factory=Geometry)


@dataclass(frozen=True)
class EngineConfig:
    """Options accepted by :class:`befisc_reportforge.PDFEngine`.

    ``font_family``      "helvetica" (default, metric-identical to the
                         reference) or "roboto" (bundled TTF, full Unicode).
    ``page_decorations`` single switch that turns on running header, running
                         footer and "Page X of Y" numbering.  Off by default
                         because the reference report has none.
    """

    template: str = "cibil_cir"
    font_family: str = "helvetica"
    page_decorations: bool = False
    assets_dir: Path = DEFAULT_ASSETS_DIR
    logo_path: Optional[Path] = None          # default: <assets_dir>/logo.svg
    running_header_text: str = "CONSUMER CIR"
    running_footer_text: str = "TransUnion CIBIL - Consumer Credit Information Report"
    title: str = "Consumer CIR"
    author: str = "befisc_reportforge"
    strict: bool = False                      # raise on non-fatal validation warnings
    use_raw_bureau_data: bool = True          # enrich from base64 OriginalData if present

    def resolved_logo(self) -> Path:
        return Path(self.logo_path) if self.logo_path else Path(self.assets_dir) / "logo.svg"

    def build_theme(self) -> Theme:
        from .exceptions import AssetError  # local import avoids a cycle

        key = (self.font_family or "helvetica").strip().lower()
        if key not in FONT_FAMILIES:
            raise AssetError(
                f"Unknown font_family {self.font_family!r}; choose one of {sorted(FONT_FAMILIES)}"
            )
        return Theme(font=FONT_FAMILIES[key])

    def with_options(self, **changes) -> "EngineConfig":
        return replace(self, **changes)
