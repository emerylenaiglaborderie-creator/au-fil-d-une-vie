"""Traduction de l'interface : français (langue source) et anglais.

Principe de gettext, sans dépendance : chaque phrase de l'interface passe par `_()`.
La phrase française sert de clé ; `_()` renvoie sa traduction dans la langue
choisie, ou la phrase elle-même en français. Les phrases avec des valeurs variables
utilisent des emplacements nommés : `_("Bonjour {name}").format(name=prenom)`.

Un test vérifie que chaque `_("...")` du code a sa traduction anglaise.
"""

from au_fil_d_une_vie.i18n_en import EN

LANGUAGES = {"fr": "Français", "en": "English"}
SOURCE = "fr"

_CATALOGS: dict[str, dict[str, str]] = {"en": EN}
_current = SOURCE

MONTHS_SHORT = {
    "fr": ("janv.", "févr.", "mars", "avr.", "mai", "juin",
           "juil.", "août", "sept.", "oct.", "nov.", "déc."),
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}  # fmt: skip

MONTHS_LONG = {
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"),
    "en": ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"),
}  # fmt: skip


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else SOURCE


def language() -> str:
    return _current


def _(text: str) -> str:
    """Traduction de `text` (phrase française) dans la langue choisie."""
    if _current == SOURCE:
        return text
    return _CATALOGS[_current].get(text, text)


def plural(count: int, singular: str, plural_form: str) -> str:
    """« 1 récit », « 6 récits » : les deux formes passent par `_()`.

    Le français met le singulier à 0 (« 0 récit ») ; l'anglais, le pluriel (« 0 stories »).
    """
    one = count <= 1 if _current == "fr" else count == 1
    return f"{count} {_(singular) if one else _(plural_form)}"


def short_date(day: int, month: int, year: int) -> str:
    months = MONTHS_SHORT[_current]
    if _current == "en":
        return f"{months[month - 1]} {day}, {year}"
    return f"{day} {months[month - 1]} {year}"


def long_date(day: int, month: int, year: int) -> str:
    months = MONTHS_LONG[_current]
    if _current == "en":
        return f"{months[month - 1]} {day}, {year}"
    return f"{day} {months[month - 1]} {year}"
