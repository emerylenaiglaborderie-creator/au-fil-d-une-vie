"""La traduction anglaise est complète : chaque phrase passée à _() a sa traduction."""

import ast
import re
from pathlib import Path

import pytest

from au_fil_d_une_vie import i18n
from au_fil_d_une_vie.i18n_en import EN

SRC = Path(__file__).resolve().parent.parent / "src" / "au_fil_d_une_vie"


def _module_strings(tree: ast.Module) -> dict[str, list[str]]:
    """Constantes de module qui contiennent du texte (chaîne, tuple de chaînes ou de couples)."""
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                values = [
                    n.value
                    for n in ast.walk(node.value)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                ]
                found[target.id] = values
    return found


def phrases_a_traduire() -> set[str]:
    phrases: set[str] = set()
    for path in SRC.rglob("*.py"):
        if path.name in {"i18n.py", "i18n_en.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = _module_strings(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            )
            args = node.args
            if name == "_" and args:
                arg = args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    phrases.add(arg.value)
                elif isinstance(arg, ast.Name) and arg.id in constants:
                    phrases.update(constants[arg.id])
                elif isinstance(arg, ast.Name):
                    # _(tip) dans une boucle sur une constante : on ajoute tout le contenu de
                    # la constante parcourue (LISTENING_TIPS, THEME_CHOICES...).
                    for loop in ast.walk(tree):
                        if not isinstance(loop, (ast.For, ast.comprehension)):
                            continue
                        iterated = loop.iter
                        if isinstance(iterated, ast.Call) and iterated.args:  # enumerate(X)
                            iterated = iterated.args[0]
                        if not isinstance(iterated, ast.Name) or iterated.id not in constants:
                            continue
                        targets = [n.id for n in ast.walk(loop.target) if isinstance(n, ast.Name)]
                        if arg.id in targets:
                            # Seulement le texte, pas les identifiants (« auto », « light »...).
                            phrases.update(
                                v for v in constants[iterated.id] if not re.fullmatch(r"[a-z_]+", v)
                            )
            elif name == "plural" and len(args) == 3:
                for arg in args[1:]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        phrases.add(arg.value)
    return phrases


def test_chaque_phrase_a_sa_traduction_anglaise() -> None:
    manquantes = sorted(p for p in phrases_a_traduire() if p not in EN)
    assert manquantes == [], "Traductions manquantes :\n" + "\n".join(manquantes)


def test_les_emplacements_sont_les_memes() -> None:
    for francais, anglais in EN.items():
        assert set(re.findall(r"{(\w+)}", francais)) == set(re.findall(r"{(\w+)}", anglais)), (
            francais
        )


def test_changer_de_langue() -> None:
    i18n.set_language("en")
    try:
        assert i18n._("Ma quête") == "My quest"
        assert i18n.plural(2, "récit", "récits") == "2 stories"
        assert i18n.short_date(12, 10, 2026) == "Oct 12, 2026"
    finally:
        i18n.set_language("fr")
    assert i18n._("Ma quête") == "Ma quête"
    assert i18n.short_date(12, 10, 2026) == "12 oct. 2026"


@pytest.mark.parametrize("code", ["xx", ""])
def test_une_langue_inconnue_revient_au_francais(code: str) -> None:
    i18n.set_language(code)
    assert i18n.language() == "fr"
