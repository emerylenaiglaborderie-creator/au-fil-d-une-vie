"""Tests de l'interface (pytest-qt), sur une base de démo temporaire."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget
from pytestqt.qtbot import QtBot

from au_fil_d_une_vie.bootstrap import Services, open_services
from au_fil_d_une_vie.services.fake_audio import FakeAudioInput, tone
from au_fil_d_une_vie.services.recording import RecordingState
from au_fil_d_une_vie.ui.app import create_application
from au_fil_d_une_vie.ui.main_window import MainWindow
from au_fil_d_une_vie.ui.widgets import ClickableFrame, LeafToggle, PrimaryButton


@pytest.fixture(autouse=True)
def theme_jour() -> Iterator[None]:
    """Chaque test repart du thème Jour et du français, même si un test les a changés."""
    from au_fil_d_une_vie import i18n
    from au_fil_d_une_vie.ui import theme

    yield
    theme.apply(False)
    i18n.set_language("fr")


@pytest.fixture
def micro() -> FakeAudioInput:
    return FakeAudioInput()


@pytest.fixture
def services(micro: FakeAudioInput, tmp_path: Path) -> Services:
    return open_services(
        demo=True,
        microphone=lambda: micro,
        models_dir=tmp_path / "modeles",
        settings_path=tmp_path / "settings.json",
    )


@pytest.fixture
def window(qtbot: QtBot, services: Services) -> Iterator[MainWindow]:
    create_application([])
    fenetre = MainWindow(services)
    # Jamais de boîte de dialogue bloquante pendant les tests.
    fenetre.interview.confirm = lambda question: True  # type: ignore[method-assign]
    qtbot.addWidget(fenetre)
    yield fenetre
    fenetre.interview.abandon()


def _texte_question(window: MainWindow) -> str:
    piste = window.quest._track
    assert piste is not None
    return piste.question.text


def test_l_accueil_salue_et_propose_une_piste(window: MainWindow) -> None:
    assert window.quest._hello.text() == "Bonjour Camille"
    assert _texte_question(window) == "Quelle chanson te rappelle ta jeunesse ?"


def test_une_autre_piste_change_la_question(qtbot: QtBot, window: MainWindow) -> None:
    avant = _texte_question(window)
    bouton = next(
        b for b in window.quest.findChildren(QPushButton) if b.text() == "Une autre piste"
    )
    qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)
    assert _texte_question(window) != avant


def test_lancer_l_interview_avec_la_personne_choisie(qtbot: QtBot, window: MainWindow) -> None:
    papa = next(t for t in window.quest.findChildren(LeafToggle) if t.text() == "Papa")
    qtbot.mouseClick(papa, Qt.MouseButton.LeftButton)
    lancer = window.quest.findChild(PrimaryButton)
    assert lancer is not None
    with qtbot.waitSignal(window.quest.interview_requested) as signal:
        qtbot.mouseClick(lancer, Qt.MouseButton.LeftButton)
    question_id, person_id = signal.args
    piste = window.quest._track
    assert piste is not None and question_id == piste.question.id
    assert person_id == window.quest._people.checkedId()
    assert window._stack.currentIndex() == MainWindow.INTERVIEW


def test_la_navigation_change_d_ecran(window: MainWindow) -> None:
    window.show_screen(MainWindow.GRAPH)
    assert window._stack.currentIndex() == MainWindow.GRAPH
    window.show_screen(MainWindow.QUEST)
    assert window._stack.currentIndex() == MainWindow.QUEST


# Interview


@pytest.fixture
def interview(qtbot: QtBot, window: MainWindow) -> MainWindow:
    papa = next(t for t in window.quest.findChildren(LeafToggle) if t.text() == "Papa")
    qtbot.mouseClick(papa, Qt.MouseButton.LeftButton)
    lancer = window.quest.findChild(PrimaryButton)
    assert lancer is not None
    qtbot.mouseClick(lancer, Qt.MouseButton.LeftButton)
    return window


def test_l_interview_reprend_la_piste_et_la_personne(interview: MainWindow) -> None:
    ecran = interview.interview
    assert ecran._question.text() == "Quelle chanson te rappelle ta jeunesse ?"
    assert ecran._person.currentText() == "Papa"
    assert "Papa sait que la conversation est enregistrée" in ecran._consent.text.text()


def test_on_ne_peut_pas_enregistrer_sans_l_accord(interview: MainWindow) -> None:
    ecran = interview.interview
    assert not ecran._consent.is_checked()
    assert not ecran._start.isEnabled()
    ecran._consent.set_checked(True)
    assert ecran._start.isEnabled()


def test_changer_de_personne_retire_l_accord(interview: MainWindow) -> None:
    ecran = interview.interview
    ecran._consent.set_checked(True)
    ecran._person.setCurrentIndex(ecran._person.findText("Tonton Alain"))
    assert not ecran._consent.is_checked()


def test_enregistrer_puis_terminer_cree_le_recit(
    qtbot: QtBot, interview: MainWindow, micro: FakeAudioInput, services: Services
) -> None:
    ecran = interview.interview
    ecran._consent.set_checked(True)
    qtbot.mouseClick(ecran._start, Qt.MouseButton.LeftButton)
    assert services.recording.state is RecordingState.RECORDING
    assert not ecran._person.isEnabled()

    micro.hear(tone(2.0))
    with qtbot.waitSignal(ecran.story_saved) as signal:
        qtbot.mouseClick(ecran._finish, Qt.MouseButton.LeftButton)

    assert services.recording.state is RecordingState.IDLE
    assert ecran._done.isVisibleTo(ecran)
    assert "Papa" in ecran._done_text.text()
    story_id = signal.args[0]
    fichiers = list(services.audio_dir.rglob("*.wav"))
    assert len(fichiers) == 1
    vue = services.quest.overview()
    assert vue.story_count == 7
    assert story_id > 0


def test_pause_et_reprise(qtbot: QtBot, interview: MainWindow, services: Services) -> None:
    ecran = interview.interview
    ecran._consent.set_checked(True)
    qtbot.mouseClick(ecran._start, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(ecran._pause, Qt.MouseButton.LeftButton)
    assert services.recording.state is RecordingState.PAUSED
    assert ecran._resume.isVisibleTo(ecran) and not ecran._pause.isVisibleTo(ecran)
    qtbot.mouseClick(ecran._resume, Qt.MouseButton.LeftButton)
    assert services.recording.state is RecordingState.RECORDING


def test_recommencer_efface_apres_confirmation(
    qtbot: QtBot, interview: MainWindow, micro: FakeAudioInput, services: Services
) -> None:
    ecran = interview.interview
    ecran._consent.set_checked(True)
    qtbot.mouseClick(ecran._start, Qt.MouseButton.LeftButton)
    micro.hear(tone(1.0))

    ecran.confirm = lambda question: False  # type: ignore[method-assign]
    qtbot.mouseClick(ecran._restart, Qt.MouseButton.LeftButton)
    assert services.recording.state is RecordingState.RECORDING

    ecran.confirm = lambda question: True  # type: ignore[method-assign]
    qtbot.mouseClick(ecran._restart, Qt.MouseButton.LeftButton)
    assert services.recording.state is RecordingState.IDLE
    assert list(services.audio_dir.rglob("*.wav")) == []


def test_quitter_l_ecran_pendant_l_enregistrement(
    qtbot: QtBot, interview: MainWindow, services: Services
) -> None:
    ecran = interview.interview
    ecran._consent.set_checked(True)
    qtbot.mouseClick(ecran._start, Qt.MouseButton.LeftButton)

    ecran.confirm = lambda question: False  # type: ignore[method-assign]
    interview.show_screen(MainWindow.QUEST)
    assert interview._stack.currentIndex() == MainWindow.INTERVIEW

    ecran.confirm = lambda question: True  # type: ignore[method-assign]
    interview.show_screen(MainWindow.QUEST)
    assert interview._stack.currentIndex() == MainWindow.QUEST
    assert services.recording.state is RecordingState.IDLE


def test_d_autres_pistes_changent_la_question(qtbot: QtBot, interview: MainWindow) -> None:
    from au_fil_d_une_vie.ui.widgets import ClickableFrame

    ecran = interview.interview
    avant = ecran._question.text()
    ligne = ecran._aside.parentWidget().findChildren(ClickableFrame)[0]  # type: ignore[union-attr]
    qtbot.mouseClick(ligne, Qt.MouseButton.LeftButton)
    assert ecran._question.text() != avant


# Transcription


def _installer_faux_modele(services: Services) -> None:
    from tests.test_transcription_queue import FauxWhisper

    dossier = services.models.path(services.model_size)
    dossier.mkdir(parents=True)
    (dossier / "model.bin").write_bytes(b"")
    services.transcription._transcriber_factory = FauxWhisper  # type: ignore[method-assign]


def test_sans_modele_le_pied_de_page_propose_l_installation(window: MainWindow) -> None:
    window._refresh_job_status()
    assert window._job_text.text() == "Modèle de transcription non installé."
    assert window._install.isVisibleTo(window)


def test_la_fenetre_du_modele_ne_telecharge_rien_sans_accord(
    qtbot: QtBot, window: MainWindow, services: Services
) -> None:
    from au_fil_d_une_vie.ui.model_setup import ModelSetupDialog

    dialogue = ModelSetupDialog(services.models, services.model_size, window)
    qtbot.addWidget(dialogue)
    dialogue._later.click()
    assert not services.transcription_ready()
    assert not services.models.path(services.model_size).exists()


def test_un_recit_enregistre_est_transcrit_en_arriere_plan(
    qtbot: QtBot, interview: MainWindow, micro: FakeAudioInput, services: Services
) -> None:
    _installer_faux_modele(services)
    ecran = interview.interview
    ecran._consent.set_checked(True)
    qtbot.mouseClick(ecran._start, Qt.MouseButton.LeftButton)
    micro.hear(tone(1.5))
    with qtbot.waitSignal(interview._bridge.finished, timeout=10_000):
        qtbot.mouseClick(ecran._finish, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: interview._job_text.text() == "Le texte du récit est prêt.")
    services.transcription.shutdown(5)


# Récits et fiche


def test_la_liste_des_recits(window: MainWindow) -> None:
    from au_fil_d_une_vie.ui.screens.stories import StoryEntry

    window.show_screen(MainWindow.STORIES)
    entrees = window.stories.findChildren(StoryEntry)
    assert len(entrees) == 6
    assert entrees[0].card.question == "Comment était ton école quand tu étais petite ?"


def test_rechercher_un_recit(qtbot: QtBot, window: MainWindow) -> None:
    from au_fil_d_une_vie.ui.screens.stories import StoryEntry

    window.show_screen(MainWindow.STORIES)
    window.stories._search.setText("mobylette")
    window.stories._search_timer.timeout.emit()
    visibles = [e for e in window.stories.findChildren(StoryEntry) if e.parent() is not None]
    assert [e.card.person_name for e in visibles] == ["Tonton Alain"]


def test_une_tuile_de_piste_ouvre_les_recits_filtres(qtbot: QtBot, window: MainWindow) -> None:
    from au_fil_d_une_vie.ui.screens.stories import StoryEntry
    from au_fil_d_une_vie.ui.widgets import ClickableFrame

    tuile = next(
        t
        for t in window.quest.findChildren(ClickableFrame)
        if t.objectName() == "tile" and t.accessibleName().startswith("Cuisine")
    )
    qtbot.mouseClick(tuile, Qt.MouseButton.LeftButton)
    assert window._stack.currentIndex() == MainWindow.STORIES
    themes = {e.card.theme_label for e in window.stories.findChildren(StoryEntry) if e.parent()}
    assert themes == {"Cuisine"}


@pytest.fixture
def fiche(window: MainWindow, services: Services) -> MainWindow:
    window.show_story(services.stories.cards()[0].id)
    return window


def test_la_fiche_affiche_le_recit_surligne(fiche: MainWindow) -> None:
    ecran = fiche.story
    assert fiche._stack.currentIndex() == MainWindow.STORY
    assert ecran._teller.text() == "Mamie Yvonne raconte"
    assert "background-color" in ecran._text.text()
    assert fiche._nav.checkedId() == MainWindow.STORIES


def test_corriger_la_transcription_depuis_l_onglet_brut(
    qtbot: QtBot, fiche: MainWindow, services: Services
) -> None:
    ecran = fiche.story
    qtbot.mouseClick(ecran._tab_raw, Qt.MouseButton.LeftButton)
    assert ecran._correct.text() == "Corriger la transcription"
    qtbot.mouseClick(ecran._correct, Qt.MouseButton.LeftButton)
    assert ecran._editor.isVisibleTo(ecran)
    ecran._editor.setPlainText("L'école, c'était au bourg, chez Mademoiselle Le Gall.")
    ecran._save_text()
    detail = services.stories.detail(ecran.story_id or 0)
    assert detail is not None
    assert detail.raw_text == "L'école, c'était au bourg, chez Mademoiselle Le Gall."
    assert detail.book_text is None
    assert not ecran._editor.isVisibleTo(ecran)


def test_corriger_la_version_livre(qtbot: QtBot, fiche: MainWindow, services: Services) -> None:
    ecran = fiche.story
    qtbot.mouseClick(ecran._correct, Qt.MouseButton.LeftButton)
    ecran._editor.setPlainText("Version pour le livre.")
    ecran._save_text()
    detail = services.stories.detail(ecran.story_id or 0)
    assert detail is not None and detail.book_text == "Version pour le livre."
    assert detail.raw_text is not None and detail.raw_text.startswith("L'école")


def test_retirer_puis_ajouter_un_mot_cle(fiche: MainWindow, services: Services) -> None:
    ecran = fiche.story
    story_id = ecran.story_id or 0
    detail = services.stories.detail(story_id)
    assert detail is not None
    ecran._remove_word(detail.tags[0].keyword_id)
    ecran._new_word.setText("Le Gall")
    ecran._add_word()
    detail = services.stories.detail(story_id)
    assert detail is not None
    assert "Le Gall" in {t.label for t in detail.tags}


def test_le_carnet_est_garde_en_quittant_la_fiche(fiche: MainWindow, services: Services) -> None:
    ecran = fiche.story
    story_id = ecran.story_id or 0
    ecran._note.setPlainText("Retrouver une photo de l'école.")
    fiche.show_screen(MainWindow.STORIES)
    detail = services.stories.detail(story_id)
    assert detail is not None and detail.note == "Retrouver une photo de l'école."


def test_masquer_puis_supprimer_un_recit(fiche: MainWindow, services: Services) -> None:
    ecran = fiche.story
    story_id = ecran.story_id or 0
    ecran._toggle_hidden()
    carte = next(c for c in services.stories.cards() if c.id == story_id)
    assert carte.is_hidden

    ecran.confirm = lambda question: False  # type: ignore[method-assign]
    ecran._delete()
    assert services.stories.detail(story_id) is not None

    ecran.confirm = lambda question: True  # type: ignore[method-assign]
    ecran._delete()
    assert services.stories.detail(story_id) is None
    assert fiche._stack.currentIndex() == MainWindow.STORIES


# Graphe


def test_le_graphe_selectionne_le_recit_le_plus_relie(
    window: MainWindow, services: Services
) -> None:
    window.show_screen(MainWindow.GRAPH)
    ecran = window.graph
    premier = services.stories.cards()[0]
    assert ecran._selected == premier.id
    assert ecran._card_question.text() == premier.question
    assert ecran._card_person.text() == "Mamie Yvonne"


def test_cliquer_un_point_du_graphe_le_selectionne(qtbot: QtBot, window: MainWindow) -> None:
    window.show_screen(MainWindow.GRAPH)
    ecran = window.graph
    vue = ecran._view
    assert vue is not None
    autre = next(s for s in vue.stories if s.id != ecran._selected)
    point = ecran._board._point(autre.x, autre.y).toPoint()
    qtbot.mouseClick(ecran._board, Qt.MouseButton.LeftButton, pos=point)
    assert ecran._selected == autre.id
    assert ecran._card_question.text() == autre.question


def test_ouvrir_la_fiche_depuis_le_graphe(qtbot: QtBot, window: MainWindow) -> None:
    window.show_screen(MainWindow.GRAPH)
    qtbot.mouseClick(window.graph._open, Qt.MouseButton.LeftButton)
    assert window._stack.currentIndex() == MainWindow.STORY
    assert window.story.story_id == window.graph._selected


def test_masquer_les_mots_communs(window: MainWindow) -> None:
    window.show_screen(MainWindow.GRAPH)
    window.graph._words.setChecked(False)
    assert not window.graph._board._show_words


def test_les_titres_du_graphe_tiennent_sur_deux_lignes(window: MainWindow) -> None:
    from PySide6.QtGui import QFontMetrics

    from au_fil_d_une_vie.ui import theme
    from au_fil_d_une_vie.ui.screens.graph import two_lines

    metrics = QFontMetrics(theme.font(theme.SERIF, 15, italic=True))
    assert two_lines("Court", metrics, 134) == ["Court"]
    lignes = two_lines(
        "Quel plat te rappelle ton enfance quand tu étais tout petit ?", metrics, 134
    )
    assert len(lignes) == 2 and lignes[1].endswith("…")
    assert all(metrics.horizontalAdvance(ligne) <= 134 for ligne in lignes)
    deux = two_lines("Comment as-tu rencontré Papi ?", metrics, 134)
    assert " ".join(deux) == "Comment as-tu rencontré Papi ?"


# Livre de famille


def test_la_fiche_ajoute_et_retire_du_livre(fiche: MainWindow, services: Services) -> None:
    ecran = fiche.story
    story_id = ecran.story_id or 0
    assert ecran._book.text() == "Retirer du livre de famille"  # la démo est déjà dans le livre
    ecran._toggle_book()
    carte = next(c for c in services.stories.cards() if c.id == story_id)
    assert not carte.in_book
    assert ecran._book.text() == "Ajouter au livre de famille"


def test_creer_le_livre_depuis_la_fenetre(
    qtbot: QtBot, window: MainWindow, services: Services, tmp_path: Path
) -> None:
    dialogue = window.open_book()
    qtbot.addWidget(dialogue)
    assert dialogue._count.text() == "6 récits choisis"
    dialogue._check_all(False)
    assert not dialogue._create.isEnabled()
    dialogue._check_all(True)
    chemin = tmp_path / "livre.pdf"
    with qtbot.waitSignal(dialogue.created, timeout=20_000):
        dialogue.export_to(chemin)
    assert chemin.read_bytes().startswith(b"%PDF")
    assert dialogue._done.isVisibleTo(dialogue)


# Premier lancement et proches


@pytest.fixture
def neuve(qtbot: QtBot, tmp_path: Path, micro: FakeAudioInput) -> Iterator[MainWindow]:
    """Fenêtre sur une base neuve, comme au tout premier lancement."""
    from au_fil_d_une_vie.bootstrap import build_services
    from au_fil_d_une_vie.repositories import connect
    from au_fil_d_une_vie.services.tracks import seed_tracks

    create_application([])
    db = tmp_path / "base.db"
    conn = connect(db)
    seed_tracks(conn)
    services = build_services(
        conn,
        db,
        tmp_path / "audio",
        lambda: micro,
        tmp_path / "modeles",
        settings_path=tmp_path / "settings.json",
    )
    fenetre = MainWindow(services)
    fenetre.interview.confirm = lambda question: True  # type: ignore[method-assign]
    qtbot.addWidget(fenetre)
    yield fenetre
    fenetre.interview.abandon()


def test_le_premier_lancement_commence_par_l_accueil(neuve: MainWindow) -> None:
    assert neuve._stack.currentIndex() == MainWindow.WELCOME
    assert not neuve._nav_box.isVisibleTo(neuve)
    assert not neuve.welcome._start.isEnabled()


def test_sous_15_ans_l_accord_parental_debloque_le_depart(qtbot: QtBot, neuve: MainWindow) -> None:
    accueil = neuve.welcome
    accueil._name.setText("Léo")
    accueil._age.button(accueil.YOUNGER).click()
    assert accueil._parent.isVisibleTo(accueil)
    assert not accueil._start.isEnabled()
    accueil._parent_consent.set_checked(True)
    assert accueil._start.isEnabled()


def test_terminer_l_accueil_ouvre_la_quete(qtbot: QtBot, neuve: MainWindow) -> None:
    accueil = neuve.welcome
    accueil._name.setText("Camille")
    accueil._age.button(accueil.OLDER).click()
    accueil._person.set_values("Mamie Jeanne", "grand-mère")
    accueil._person.button.click()
    accueil._person.set_values("mamie jeanne", "grand-mère")
    accueil._person.button.click()  # doublon refusé
    assert accueil._person_error.isVisibleTo(accueil)
    qtbot.mouseClick(accueil._start, Qt.MouseButton.LeftButton)

    assert neuve._stack.currentIndex() == MainWindow.QUEST
    assert neuve._nav_box.isVisibleTo(neuve)
    assert neuve.quest._hello.text() == "Bonjour Camille"
    assert neuve.quest._track is not None
    assert neuve.quest._people.checkedId() > 0


def test_gerer_les_proches(qtbot: QtBot, window: MainWindow, services: Services) -> None:
    dialogue = window.open_people()
    qtbot.addWidget(dialogue)
    dialogue.form.set_values("Cousine Inès", "cousine")
    dialogue.form.button.click()
    noms = [p.display_name for p, _ in services.people.all()]
    assert "Cousine Inès" in noms

    ines = next(p for p, _ in services.people.all() if p.display_name == "Cousine Inès")
    dialogue._start_edit(ines)
    dialogue.form.set_values("Inès", "cousine")
    dialogue.form.button.click()
    assert "Inès" in [p.display_name for p, _ in services.people.all()]

    dialogue.confirm = lambda question: True  # type: ignore[method-assign]
    dialogue._delete(next(p for p, _ in services.people.all() if p.display_name == "Inès"), 0)
    assert "Inès" not in [p.display_name for p, _ in services.people.all()]


# Paramètres


def test_changer_son_prenom_dans_les_parametres(window: MainWindow, services: Services) -> None:
    window.show_screen(MainWindow.SETTINGS)
    ecran = window.settings
    ecran._name.setText("Camille-Rose")
    ecran._save_name()
    profil = services.profile.get()
    assert profil is not None and profil.first_name == "Camille-Rose"
    window.show_screen(MainWindow.QUEST)
    assert window.quest._hello.text() == "Bonjour Camille-Rose"


def test_choisir_le_theme_nuit_reconstruit_la_fenetre(
    qtbot: QtBot, window: MainWindow, services: Services
) -> None:
    from au_fil_d_une_vie.ui import theme
    from au_fil_d_une_vie.ui.app import Controller, create_application

    controleur = Controller(create_application([]), services)
    ancienne = controleur.window
    qtbot.addWidget(ancienne)
    ancienne.show_screen(MainWindow.SETTINGS)
    ancienne.settings._themes.button(2).click()  # Nuit

    assert services.settings.load().theme == "dark"
    assert controleur.window is not ancienne
    assert controleur.window.current_screen() == MainWindow.SETTINGS
    assert theme.DARK_MODE
    qtbot.addWidget(controleur.window)


# Pistes personnalisables


def test_creer_une_piste_et_une_question(
    qtbot: QtBot, window: MainWindow, services: Services
) -> None:
    dialogue = window.open_tracks()
    qtbot.addWidget(dialogue)
    dialogue._new_theme.setText("Voyages")
    dialogue._add_theme()
    assert dialogue._theme_name.text() == "Voyages"
    dialogue._question.setText("Quel a été ton plus beau voyage ?")
    dialogue._submit_question()
    voyages = next(t for t in services.tracks.all() if t.theme.label == "Voyages")
    assert [q.question.text for q in voyages.questions] == ["Quel a été ton plus beau voyage ?"]
    dialogue.accept()
    tuiles = [
        t.accessibleName()
        for t in window.quest.findChildren(ClickableFrame)
        if t.objectName() == "tile"
    ]
    assert any(nom.startswith("Voyages") for nom in tuiles)


def test_une_piste_avec_des_recits_reste(
    qtbot: QtBot, window: MainWindow, services: Services
) -> None:
    dialogue = window.open_tracks()
    qtbot.addWidget(dialogue)
    dialogue.confirm = lambda question: True  # type: ignore[method-assign]
    enfance = next(t for t in services.tracks.all() if t.theme.label == "Enfance")
    dialogue._select(enfance.theme.id)
    dialogue._remove_theme()
    assert "Enfance" in [t.theme.label for t in services.tracks.all()]
    assert "récits" in dialogue._error.text()


def test_renommer_une_piste(qtbot: QtBot, window: MainWindow, services: Services) -> None:
    dialogue = window.open_tracks()
    qtbot.addWidget(dialogue)
    cuisine = next(t for t in services.tracks.all() if t.theme.label == "Cuisine")
    dialogue._select(cuisine.theme.id)
    dialogue._theme_name.setText("Cuisine et repas")
    dialogue._rename_theme()
    assert "Cuisine et repas" in [t.theme.label for t in services.tracks.all()]


# Langue


def test_passer_l_interface_en_anglais(qtbot: QtBot, services: Services) -> None:
    from au_fil_d_une_vie.ui.app import Controller, create_application

    controleur = Controller(create_application([]), services)
    qtbot.addWidget(controleur.window)
    controleur.window.show_screen(MainWindow.SETTINGS)
    controleur.window.settings._languages.button(1).click()  # English

    fenetre = controleur.window
    qtbot.addWidget(fenetre)
    assert services.settings.load().language == "en"
    fenetre.show_screen(MainWindow.QUEST)
    assert fenetre.quest._hello.text() == "Hello Camille"
    liens = [b.text() for b in fenetre._nav.buttons()]
    assert liens == ["My quest", "Interview", "Stories", "Graph"]


def test_une_premiere_quete_en_anglais_recoit_les_pistes_en_anglais(
    qtbot: QtBot, tmp_path: Path, micro: FakeAudioInput
) -> None:
    from au_fil_d_une_vie import i18n
    from au_fil_d_une_vie.bootstrap import build_services
    from au_fil_d_une_vie.repositories import connect

    create_application([])
    i18n.set_language("en")
    db = tmp_path / "base.db"
    services = build_services(
        connect(db), db, tmp_path / "audio", lambda: micro, tmp_path / "m", tmp_path / "s.json"
    )
    fenetre = MainWindow(services)
    qtbot.addWidget(fenetre)
    accueil = fenetre.welcome
    accueil._name.setText("Sam")
    accueil._age.button(accueil.OLDER).click()
    accueil._finish()
    pistes = [t.theme.label for t in services.tracks.all()]
    assert pistes[:2] == ["Childhood", "Encounters"]
    assert fenetre.quest._hello.text() == "Hello Sam"


def _textes_affiches(racine: QWidget) -> list[str]:
    from PySide6.QtWidgets import QAbstractButton, QLabel, QLineEdit, QPlainTextEdit

    textes: list[str] = []
    for widget in racine.findChildren(QWidget):
        if isinstance(widget, (QLabel, QAbstractButton)):
            textes.append(widget.text())
        if isinstance(widget, (QLineEdit, QPlainTextEdit)):
            textes.append(widget.placeholderText())
        textes += [widget.toolTip(), widget.accessibleName()]
    return [t for t in textes if t]


def test_aucun_francais_ne_reste_en_anglais(
    qtbot: QtBot, tmp_path: Path, micro: FakeAudioInput
) -> None:
    """Filet de sécurité : une phrase oubliée (sans _()) resterait en français à l'écran."""
    import re

    from au_fil_d_une_vie import i18n
    from au_fil_d_une_vie.bootstrap import build_services
    from au_fil_d_une_vie.repositories import connect

    create_application([])
    i18n.set_language("en")
    db = tmp_path / "base.db"
    services = build_services(
        connect(db), db, tmp_path / "audio", lambda: micro, tmp_path / "m", tmp_path / "s.json"
    )
    fenetre = MainWindow(services)
    qtbot.addWidget(fenetre)
    vus = _textes_affiches(fenetre)  # écran d'accueil
    fenetre.welcome._name.setText("Sam")
    fenetre.welcome._age.button(fenetre.welcome.OLDER).click()
    services.people.add("Grandma Jane", "grandmother")
    fenetre.welcome._finish()
    for ecran in (
        MainWindow.QUEST,
        MainWindow.INTERVIEW,
        MainWindow.STORIES,
        MainWindow.GRAPH,
        MainWindow.SETTINGS,
    ):
        fenetre.show_screen(ecran)
        vus += _textes_affiches(fenetre)
    for ouvrir in (fenetre.open_people, fenetre.open_tracks, fenetre.open_book):
        dialogue = ouvrir()
        qtbot.addWidget(dialogue)
        vus += _textes_affiches(dialogue)
        dialogue.close()

    marques = re.compile(
        r"[éèàùâêîôûçœ]|\b(le|la|les|une|des|du|ta|tes|ton|est|pas|pour|dans)\b", re.I
    )
    autorises = {"Au fil d'une vie", "Français"}
    restes = sorted(
        {t for t in vus if t not in autorises and marques.search(t.replace("Au fil d'une vie", ""))}
    )
    assert restes == [], "Texte resté en français :\n" + "\n".join(restes)
