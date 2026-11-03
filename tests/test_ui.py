"""Tests de l'interface (pytest-qt), sur une base de démo temporaire."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from au_fil_d_une_vie.bootstrap import Services, open_services
from au_fil_d_une_vie.ui.app import create_application
from au_fil_d_une_vie.ui.main_window import MainWindow
from au_fil_d_une_vie.ui.widgets import LeafToggle, PrimaryButton


@pytest.fixture
def services() -> Services:
    return open_services(demo=True)


@pytest.fixture
def window(qtbot: QtBot, services: Services) -> MainWindow:
    create_application([])
    fenetre = MainWindow(services)
    qtbot.addWidget(fenetre)
    return fenetre


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
