"""Direction artistique : couleurs, polices embarquées et feuille de style Qt."""

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

RESOURCES = Path(__file__).resolve().parent / "resources"
IMAGES = RESOURCES / "images"
FONTS = RESOURCES / "fonts"

# Couleurs (voir docs/brief.md, section 4.3)
CREAM = "#FDFCF8"
WHITE = "#FFFFFF"
INK = "#2F2F2F"
INK_SOFT = "#3B3B3B"
THREAD = "#444444"
RED = "#C73A45"
RED_SHADOW = "#8F2530"
RED_TEXT = "#B0303B"
LEAF = "#D5E6AB"
LEAF_HOVER = "#E8F0D4"
LEAF_TEXT = "#2F5A1C"
LEAF_TEXT_SOFT = "#3E6B2A"
LEAF_BORDER = "#B9C79A"
LEAF_BORDER_HOVER = "#9DBB6A"
BORDER = "#E3E6D8"
MUTED = "#5B5B5B"
NAV_MUTED = "#555555"

# Familles
SCRIPT = "Sacramento"
SANS = "Jost"
SERIF = "Lora"


def load_fonts() -> list[str]:
    """Enregistre les polices embarquées. Retourne les familles chargées."""
    families: list[str] = []
    for path in sorted(FONTS.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
    return families


def default_font() -> QFont:
    """Police de base de l'interface (les QSS ne fixent pas de police, pour ne pas
    écraser celles choisies widget par widget)."""
    return font(SANS, 17)


def font(
    family: str,
    px: int,
    weight: QFont.Weight = QFont.Weight.Normal,
    italic: bool = False,
    spacing_em: float = 0.0,
) -> QFont:
    """Police à une taille en pixels (comme dans la maquette)."""
    f = QFont(family)
    f.setPixelSize(px)
    f.setWeight(weight)
    f.setItalic(italic)
    if spacing_em:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, px * spacing_em)
    return f


def color(value: str) -> QColor:
    return QColor(value)


_LEAF_RADII = """
    border-top-left-radius: 16px;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 16px;
    border-bottom-left-radius: 3px;
"""

STYLESHEET = f"""
QWidget {{ color: {INK}; }}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget#page {{
    background: {CREAM};
}}
QScrollArea {{ border: none; }}

QWidget#header {{
    background: {WHITE};
    border-bottom: 1px solid {BORDER};
}}
QWidget#footer {{
    background: {CREAM};
    border-top: 1px solid {BORDER};
}}
QLabel#footerText {{ font-size: 14px; color: {MUTED}; }}

QPushButton#outline {{
    min-height: 44px;
    padding: 0 18px;
    border: 1.5px solid {INK_SOFT};
    border-radius: 10px;
    background: transparent;
    font-size: 15px;
    font-weight: 500;
}}
QPushButton#outline:hover {{ background: {LEAF_HOVER}; }}

QPushButton#link {{
    min-height: 44px;
    padding: 0;
    border: none;
    background: transparent;
    font-size: 15px;
    font-weight: 500;
    color: {LEAF_TEXT};
    text-decoration: underline;
}}
QPushButton#link:hover {{ color: {INK}; }}

QPushButton#leafToggle {{
    min-height: 44px;
    padding: 0 18px;
    border: 1.5px solid {LEAF_BORDER};
    {_LEAF_RADII}
    background: transparent;
    font-size: 16px;
    color: {INK_SOFT};
}}
QPushButton#leafToggle:hover {{ border-color: {LEAF_BORDER_HOVER}; }}
QPushButton#leafToggle:checked {{
    border-color: {LEAF_TEXT_SOFT};
    background: {LEAF};
    font-weight: 600;
    color: {LEAF_TEXT};
}}

QFrame#card {{
    background: {WHITE};
    border: 1px solid {BORDER};
    border-radius: 20px;
}}
QFrame#tile {{
    background: {WHITE};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame#tile:hover {{ border-color: {LEAF_BORDER_HOVER}; }}
QFrame#row {{
    border: none;
    border-bottom: 1px solid {BORDER};
    border-radius: 0;
    background: transparent;
}}
QFrame#row:hover {{ background: {LEAF_HOVER}; }}

QLabel#sectionTitle {{
    padding-bottom: 10px;
    border-bottom: 1.5px solid {INK_SOFT};
    color: {INK_SOFT};
}}
QLabel {{ background: transparent; }}

QScrollBar:vertical {{
    width: 10px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    min-height: 40px;
    border-radius: 5px;
    background: {BORDER};
}}
QScrollBar::handle:vertical:hover {{ background: {LEAF_BORDER}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""
