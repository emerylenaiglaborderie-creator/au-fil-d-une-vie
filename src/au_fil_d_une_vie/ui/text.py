"""Petits utilitaires de texte pour l'interface."""


def plural(count: int, singular: str, plural_form: str) -> str:
    """« 1 récit », « 6 récits », « aucun » n'est pas utilisé : on affiche 0."""
    return f"{count} {singular if count <= 1 else plural_form}"
