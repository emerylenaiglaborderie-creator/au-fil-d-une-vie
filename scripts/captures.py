"""Capture les écrans de l'application (jeu de démo) en PNG, sans les afficher.

    uv run python scripts/captures.py [dossier]

Par défaut, les images vont dans docs/captures/ (utilisées par le README).
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from au_fil_d_une_vie.bootstrap import open_services  # noqa: E402
from au_fil_d_une_vie.ui.app import create_application  # noqa: E402
from au_fil_d_une_vie.ui.main_window import MainWindow  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
ECRANS = {"quete": MainWindow.QUEST}


def main() -> None:
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "docs" / "captures"
    sortie.mkdir(parents=True, exist_ok=True)
    app = create_application([])
    fenetre = MainWindow(open_services(demo=True))
    fenetre.resize(1360, 1300)
    fenetre.show()
    for nom, index in ECRANS.items():
        fenetre.show_screen(index)
        app.processEvents()
        fenetre.grab().save(str(sortie / f"{nom}.png"))
        print(sortie / f"{nom}.png")


if __name__ == "__main__":
    main()
