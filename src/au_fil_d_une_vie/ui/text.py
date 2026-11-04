"""Petits utilitaires de texte pour l'interface."""

from datetime import datetime


def plural(count: int, singular: str, plural_form: str) -> str:
    """« 1 récit », « 6 récits », « aucun » n'est pas utilisé : on affiche 0."""
    return f"{count} {singular if count <= 1 else plural_form}"


MONTHS = (
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
)  # fmt: skip


def short_date(value: datetime) -> str:
    """« 12 oct. 2026 », en heure locale."""
    local = value.astimezone()
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}"


def duration(seconds: float) -> str:
    """« 4 min 12 », ou « 42 s » sous la minute."""
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes} min {secs:02d}" if minutes else f"{secs} s"


def clock(seconds: float) -> str:
    """« 01:36 »."""
    minutes, secs = divmod(int(max(0, seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


def links_label(count: int) -> str:
    return "aucun lien" if count == 0 else plural(count, "lien", "liens")
