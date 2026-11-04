"""Petits utilitaires de texte pour l'interface (selon la langue choisie)."""

from datetime import datetime

from au_fil_d_une_vie import i18n
from au_fil_d_une_vie.i18n import _

plural = i18n.plural


def short_date(value: datetime) -> str:
    """« 12 oct. 2026 » ou « Oct 12, 2026 », en heure locale."""
    local = value.astimezone()
    return i18n.short_date(local.day, local.month, local.year)


def duration(seconds: float) -> str:
    """« 4 min 12 », ou « 42 s » sous la minute."""
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes} min {secs:02d}" if minutes else f"{secs} s"


def clock(seconds: float) -> str:
    """« 01:36 »."""
    minutes, secs = divmod(int(max(0, seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


def links_label(count: int) -> str:
    return _("aucun lien") if count == 0 else plural(count, "lien", "liens")
