"""Direction artistique : couleurs, polices embarquées et feuille de style Qt."""

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

RESOURCES = Path(__file__).resolve().parent / "resources"
IMAGES = RESOURCES / "images"
FONTS = RESOURCES / "fonts"

# Couleurs : deux palettes (voir docs/brief.md, section 4.3, pour la palette Jour).
# Les noms ci-dessous sont des variables du module : `apply()` les remplace par celles
# de la palette choisie, puis l'interface est reconstruite (voir ui/app.py).

LIGHT: dict[str, str] = {
    "CREAM": "#FDFCF8",  # fond des pages
    "SURFACE": "#FFFFFF",  # fond des cartes, plaques, champs
    "ON_RED": "#FFFFFF",  # texte et icônes sur les boutons rouges
    "INK": "#2F2F2F",
    "INK_SOFT": "#3B3B3B",
    "INK_STRONG": "#2B2B2B",
    "THREAD": "#444444",
    "THREAD_SOFT": "#555555",
    "DOTTED": "#BDBDBD",
    "TRACK": "#D8DCCB",
    "RED": "#C73A45",
    "RED_SHADOW": "#8F2530",
    "RED_TEXT": "#B0303B",
    "LEAF": "#D5E6AB",
    "LEAF_HOVER": "#E8F0D4",
    "LEAF_TEXT": "#2F5A1C",
    "LEAF_TEXT_SOFT": "#3E6B2A",
    "LEAF_BORDER": "#B9C79A",
    "LEAF_BORDER_HOVER": "#9DBB6A",
    "LEAF_BULLET": "#6FA044",
    "WORD_GREEN": "#CFE3A0",
    "BORDER": "#E3E6D8",
    "SOFT_GREEN": "#F1F6E4",
    "SOFT_GREEN_BORDER": "#DCE7C3",
    "MUTED": "#5B5B5B",
    "NAV_MUTED": "#555555",
    "CHIP_OUTLINE_TEXT": "#4A4A4A",
    "DASHED": "#7A7A7A",
    "ROW_HOVER": "#F1F5E6",
    "INPUT_BORDER": "#CFD6BC",
    "QUOTE": "#444444",
}

DARK: dict[str, str] = {
    "CREAM": "#1C1B18",
    "SURFACE": "#262521",
    "ON_RED": "#FFFFFF",
    "INK": "#ECE8DF",
    "INK_SOFT": "#DDD8CC",
    "INK_STRONG": "#F4F1EA",
    "THREAD": "#CFCAC0",
    "THREAD_SOFT": "#A8A397",
    "DOTTED": "#5E5B54",
    "TRACK": "#4A4843",
    "RED": "#D04A55",
    "RED_SHADOW": "#7A1F28",
    "RED_TEXT": "#F08A93",
    "LEAF": "#3E5226",
    "LEAF_HOVER": "#2E3A22",
    "LEAF_TEXT": "#D5E6AB",
    "LEAF_TEXT_SOFT": "#B9D58A",
    "LEAF_BORDER": "#5C6B45",
    "LEAF_BORDER_HOVER": "#8FAE5E",
    "LEAF_BULLET": "#8FBF5A",
    "WORD_GREEN": "#4B6330",
    "BORDER": "#3A3833",
    "SOFT_GREEN": "#252C1E",
    "SOFT_GREEN_BORDER": "#3A4A2C",
    "MUTED": "#ABA69B",
    "NAV_MUTED": "#B3AEA3",
    "CHIP_OUTLINE_TEXT": "#D6D1C6",
    "DASHED": "#8A867C",
    "ROW_HOVER": "#2A3122",
    "INPUT_BORDER": "#4A4843",
    "QUOTE": "#CFCAC0",
}

CREAM = SURFACE = ON_RED = INK = INK_SOFT = INK_STRONG = THREAD = THREAD_SOFT = ""
DOTTED = TRACK = RED = RED_SHADOW = RED_TEXT = LEAF = LEAF_HOVER = LEAF_TEXT = ""
LEAF_TEXT_SOFT = LEAF_BORDER = LEAF_BORDER_HOVER = LEAF_BULLET = WORD_GREEN = BORDER = ""
SOFT_GREEN = SOFT_GREEN_BORDER = MUTED = NAV_MUTED = CHIP_OUTLINE_TEXT = DASHED = ""
ROW_HOVER = INPUT_BORDER = QUOTE = ""
DARK_MODE = False
WASH_OPACITY = 0.4
TREE_OPACITY = 0.5  # arbre en fond du graphe


def apply(dark: bool) -> None:
    """Choisit la palette. À appeler avant de construire les widgets."""
    global DARK_MODE, WASH_OPACITY, TREE_OPACITY
    globals().update(DARK if dark else LIGHT)
    DARK_MODE = dark
    WASH_OPACITY = 0.16 if dark else 0.4
    TREE_OPACITY = 0.22 if dark else 0.5


apply(False)


def logo_image() -> Path:
    """Logo complet le jour ; la nuit, l'arbre seul (le texte du logo est foncé)."""
    return IMAGES / ("arbre.png" if DARK_MODE else "logo.png")


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


def _asset(name: str) -> str:
    """Chemin d'image utilisable dans une feuille de style (barres obliques partout)."""
    return (IMAGES / name).as_posix()


_LEAF_RADII = """
    border-top-left-radius: 16px;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 16px;
    border-bottom-left-radius: 3px;
"""


def stylesheet() -> str:
    """Feuille de style Qt calculée avec la palette en cours."""
    return f"""
QWidget {{ color: {INK}; }}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget#page {{
    background: {CREAM};
}}
QScrollArea {{ border: none; }}

QWidget#header {{
    background: {SURFACE};
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

QPushButton#outlineLarge {{
    min-height: 56px;
    padding: 0 24px;
    border: 1.5px solid {INK_SOFT};
    border-radius: 12px;
    background: transparent;
    font-size: 16px;
    font-weight: 600;
}}
QPushButton#outlineLarge:hover {{ background: {LEAF_HOVER}; }}
QPushButton#outlineLarge:disabled, QPushButton#outline:disabled {{
    color: {LEAF_BORDER};
    border-color: {LEAF_BORDER};
}}

QPushButton#mutedLink {{
    min-height: 56px;
    padding: 0 16px;
    border: none;
    background: transparent;
    font-size: 15px;
    font-weight: 500;
    color: {NAV_MUTED};
    text-decoration: underline;
}}
QPushButton#mutedLink:hover {{ color: {INK}; }}

QPushButton#link:disabled {{ color: {LEAF_BORDER}; }}

QFrame#consent {{
    background: {SOFT_GREEN};
    border: 1px solid {SOFT_GREEN_BORDER};
    border-radius: 14px;
}}
QFrame#softCard {{
    background: {SOFT_GREEN};
    border: 1px solid {SOFT_GREEN_BORDER};
    border-radius: 18px;
}}
QFrame#plainCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {INK_SOFT};
    border-radius: 4px;
    background: {SURFACE};
}}
QCheckBox::indicator:checked {{
    border-color: {RED_SHADOW};
    background: {RED};
    image: url("{_asset("coche.svg")}");
}}
QCheckBox::indicator:disabled {{ border-color: {LEAF_BORDER}; }}

QComboBox#personPicker {{
    min-height: 44px;
    padding: 0 28px 0 4px;
    border: none;
    border-bottom: 1.5px solid {INK_SOFT};
    border-radius: 0;
    background: transparent;
}}
QComboBox#personPicker:disabled {{ color: {MUTED}; border-bottom-color: {LEAF_BORDER}; }}
QComboBox#personPicker::drop-down {{ border: none; width: 24px; }}
QComboBox#personPicker::down-arrow {{
    image: url("{_asset("chevron-nuit.svg" if DARK_MODE else "chevron.svg")}");
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    selection-background-color: {LEAF_HOVER};
    selection-color: {INK};
    padding: 4px;
}}

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
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 20px;
}}
QFrame#tile {{
    background: {SURFACE};
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

QFrame#leaf_filled, QFrame#leaf_filled_small {{
    background: {LEAF};
    border: 1px solid {LEAF};
}}
QFrame#leaf_outline, QFrame#leaf_outline_small {{
    background: transparent;
    border: 1px solid {LEAF_BORDER};
}}
QFrame#leaf_proposed, QFrame#leaf_proposed_small, QFrame#leaf_add {{
    background: transparent;
    border: 1px dashed {DASHED};
}}
QFrame#leaf_proposed:hover, QFrame#leaf_add:hover {{
    background: {LEAF_HOVER};
    border-color: {LEAF_TEXT_SOFT};
}}
QFrame#leaf_filled, QFrame#leaf_outline, QFrame#leaf_proposed, QFrame#leaf_add {{
    border-top-left-radius: 14px;
    border-top-right-radius: 2px;
    border-bottom-right-radius: 14px;
    border-bottom-left-radius: 2px;
}}
QFrame#leaf_filled_small, QFrame#leaf_outline_small, QFrame#leaf_proposed_small {{
    border-top-left-radius: 12px;
    border-top-right-radius: 2px;
    border-bottom-right-radius: 12px;
    border-bottom-left-radius: 2px;
}}
QToolButton#chipClose {{
    border: none;
    background: transparent;
    color: {MUTED};
    font-size: 15px;
    padding: 0 4px;
}}
QToolButton#chipClose:hover {{ color: {RED_TEXT}; }}

QPushButton#tab {{
    min-height: 44px;
    padding: 0 14px;
    border: none;
    border-bottom: 2.5px solid transparent;
    background: transparent;
    font-size: 15px;
    color: {NAV_MUTED};
}}
QPushButton#tab:hover {{ color: {INK}; }}
QPushButton#tab:checked {{
    border-bottom-color: {RED};
    font-weight: 600;
    color: {INK_STRONG};
}}

QLineEdit#search {{
    min-height: 44px;
    padding: 0 2px;
    border: none;
    border-bottom: 1.5px solid {INK_SOFT};
    background: transparent;
}}

QFrame#storyRow {{ border: none; border-radius: 12px; background: transparent; }}
QFrame#storyRow:hover {{ background: {ROW_HOVER}; }}
QFrame#relatedRow {{ border: none; border-radius: 10px; background: transparent; }}
QFrame#relatedRow:hover {{ background: {LEAF_HOVER}; }}

QFrame#playerCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame#article {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 20px;
}}
QPlainTextEdit#editor, QPlainTextEdit#notebook {{
    padding: 10px 12px;
    border: 1px solid {INPUT_BORDER};
    border-radius: 14px;
    background: {SURFACE};
}}
QPlainTextEdit#editor:focus, QPlainTextEdit#notebook:focus {{ border-color: {LEAF_TEXT_SOFT}; }}

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
