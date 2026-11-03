"""Tests de l'interface (pytest-qt), sur une base de démo temporaire."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from au_fil_d_une_vie.bootstrap import Services, open_services
from au_fil_d_une_vie.services.fake_audio import FakeAudioInput, tone
from au_fil_d_une_vie.services.recording import RecordingState
from au_fil_d_une_vie.ui.app import create_application
from au_fil_d_une_vie.ui.main_window import MainWindow
from au_fil_d_une_vie.ui.widgets import LeafToggle, PrimaryButton


@pytest.fixture
def micro() -> FakeAudioInput:
    return FakeAudioInput()


@pytest.fixture
def services(micro: FakeAudioInput) -> Services:
    return open_services(demo=True, microphone=lambda: micro)


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
