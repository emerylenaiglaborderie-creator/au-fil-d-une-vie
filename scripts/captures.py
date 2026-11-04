"""Capture les écrans de l'application (jeu de démo) en PNG, sans les afficher.

    uv run python scripts/captures.py [dossier]

Par défaut, les images vont dans docs/captures/ (utilisées par le README), avec
un livre de famille d'exemple (livre-exemple.pdf), tiré du jeu de démo fictif.
L'enregistrement est simulé avec un micro factice : aucun son n'est capté.
"""

import math
import os
import sys
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from au_fil_d_une_vie.bootstrap import open_services  # noqa: E402
from au_fil_d_une_vie.services.book_pdf import BookAssets, render_book  # noqa: E402
from au_fil_d_une_vie.services.fake_audio import FakeAudioInput, tone  # noqa: E402
from au_fil_d_une_vie.ui import theme  # noqa: E402
from au_fil_d_une_vie.ui.app import create_application  # noqa: E402
from au_fil_d_une_vie.ui.main_window import MainWindow  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def simuler_enregistrement(fenetre: MainWindow, micro: FakeAudioInput) -> None:
    """Interview en cours depuis 2 min 14, avec une onde variée."""
    ecran = fenetre.interview
    ecran._consent.set_checked(True)
    ecran._start_recording()
    ecran._timer.stop()
    for i in range(24):
        amplitude = int(4000 + 14000 * abs(math.sin(i * 0.9)) * (0.6 + 0.4 * math.cos(i * 0.37)))
        micro.hear(tone(0.1, amplitude))
        ecran._wave.commit()
    micro.hear(bytes(int(16_000 * (134 - 2.4)) * 2))  # le reste de la durée, en silence
    ecran._tick()


def main() -> None:
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "docs" / "captures"
    sortie.mkdir(parents=True, exist_ok=True)
    app = create_application([])
    micro = FakeAudioInput()
    services = open_services(demo=True, microphone=lambda: micro)
    fenetre = MainWindow(services)
    fenetre.interview.confirm = lambda question: True  # type: ignore[method-assign]
    fenetre.resize(1360, 1300)
    fenetre.show()

    def capturer(nom: str) -> None:
        app.processEvents()
        fenetre.grab().save(str(sortie / f"{nom}.png"))
        print(sortie / f"{nom}.png")

    fenetre.show_screen(MainWindow.QUEST)
    capturer("quete")

    piste = services.quest.next_track()
    yvonne = services.quest.people()[0]
    assert piste is not None
    fenetre.interview.open(piste.question.id, yvonne.id)
    fenetre.show_screen(MainWindow.INTERVIEW)
    simuler_enregistrement(fenetre, micro)
    capturer("interview")
    fenetre.interview.abandon()

    fenetre.show_screen(MainWindow.STORIES)
    capturer("recits")

    premier = services.stories.cards()[0]
    fiche = services.stories.detail(premier.id)
    assert fiche is not None
    fiche.audio_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(fiche.audio_path), "wb") as wav:  # silence, pour activer le lecteur
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(bytes(32_000))
    services.stories.save_note(premier.id, "Demander à Papa s'il a connu Mademoiselle Le Gall.")
    fenetre.show_story(premier.id)
    fenetre.story._player._seek.set_fraction(0.38)
    fenetre.story._player._position.setText("01:36")
    capturer("recit")

    fenetre.show_screen(MainWindow.GRAPH)
    capturer("graphe")

    livre = render_book(
        services.book.gather(),
        sortie / "livre-exemple.pdf",
        BookAssets(theme.FONTS, theme.IMAGES / "logo.png"),
    )
    print(livre)


if __name__ == "__main__":
    main()
