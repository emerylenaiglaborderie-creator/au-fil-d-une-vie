"""Écran « Interview » : la question, l'accord du proche et l'enregistreur."""

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.services.quest import QuestService, Track
from au_fil_d_une_vie.services.recording import (
    RecordingError,
    RecordingService,
    RecordingState,
    consent_statement,
)
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.widgets import (
    ClickableFrame,
    ConsentBox,
    LeafBullet,
    PrimaryButton,
    ThreadWave,
    clear_layout,
    eyebrow,
    label,
    link_button,
    outline_button,
    paint_dot,
    section_title,
    soft_shadow,
)

LISTENING_TIPS = (
    "Laisse des silences : souvent, la personne continue.",
    "Écoute avant de corriger ou de compléter.",
    "Pose une seule question à la fois.",
)


def format_clock(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes} min {secs:02d}" if minutes else f"{secs} s"


class StatusDot(QWidget):
    """Point d'état de l'enregistreur : plein pendant l'enregistrement, vide sinon."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(14, 16)
        self.filled = False

    def paintEvent(self, event: QPaintEvent) -> None:
        paint_dot(QPainter(self), QPointF(7, 7), 12, self.filled)


class InterviewScreen(QWidget):
    story_saved = Signal(int)
    back_to_quest = Signal()
    manage_people = Signal()

    TICK_MS = 100

    def __init__(
        self, quest: QuestService, recording: RecordingService, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._quest = quest
        self._recording = recording
        self._track: Track | None = None
        self._skipped: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

        root = QHBoxLayout(self)
        root.setContentsMargins(48, 44, 48, 28)
        root.setSpacing(56)
        root.addLayout(self._build_main(), 1)
        aside = QWidget()
        aside.setFixedWidth(380)
        self._aside = QVBoxLayout(aside)
        self._aside.setContentsMargins(0, 16, 0, 0)
        self._aside.setSpacing(36)
        root.addWidget(aside, 0, Qt.AlignmentFlag.AlignTop)

        self._recording.on_level = self._wave.push
        self._update_state()

    # Construction

    def _build_main(self) -> QVBoxLayout:
        main = QVBoxLayout()
        main.setSpacing(26)

        head = QVBoxLayout()
        head.setSpacing(4)
        self._eyebrow = eyebrow("")
        head.addWidget(self._eyebrow)
        head.addWidget(label(_("Pose-lui la question..."), theme.SCRIPT, 64, color=theme.RED_TEXT))
        self._question = label("", theme.SERIF, 52, QFont.Weight.Medium, wrap=True)
        head.addWidget(self._question)
        main.addLayout(head)

        who = QHBoxLayout()
        who.setSpacing(12)
        who.addWidget(eyebrow(_("Tu interroges"), color=theme.MUTED, spacing_em=0.14))
        self._person = QComboBox()
        self._person.setObjectName("personPicker")
        self._person.setFont(theme.font(theme.SERIF, 19, italic=True))
        self._person.setCursor(Qt.CursorShape.PointingHandCursor)
        self._person.setMinimumWidth(200)
        self._person.currentIndexChanged.connect(self._person_changed)
        who.addWidget(self._person)
        who.addSpacing(16)
        self._change = link_button(_("Changer de question"))
        self._change.clicked.connect(self._change_question)
        who.addWidget(self._change)
        who.addSpacing(16)
        self._add_person = link_button(_("Ajouter un proche"))
        self._add_person.clicked.connect(self.manage_people)
        who.addWidget(self._add_person)
        who.addStretch(1)
        main.addLayout(who)

        self._consent = ConsentBox()
        self._consent.toggled.connect(lambda _checked: self._update_state())
        main.addWidget(self._consent)

        main.addWidget(self._build_recorder())

        main.addWidget(
            label(
                _(
                    "À la fin, le texte du récit est préparé sur cet ordinateur. Tu pourras "
                    "ensuite le relire et le corriger avant de l'ajouter à tes récits."
                ),
                theme.SERIF,
                16,
                color=theme.MUTED,
                italic=True,
                wrap=True,
            )
        )
        main.addStretch(1)
        return main

    def _build_recorder(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        soft_shadow(card)
        box = QVBoxLayout(card)
        box.setContentsMargins(34, 30, 34, 34)
        box.setSpacing(20)

        # Panneau d'enregistrement
        self._recorder = QWidget()
        rec = QVBoxLayout(self._recorder)
        rec.setContentsMargins(0, 0, 0, 0)
        rec.setSpacing(20)
        top = QHBoxLayout()
        self._dot = StatusDot()
        top.addWidget(self._dot)
        top.addSpacing(6)
        self._status = eyebrow("", color=theme.RED_TEXT, spacing_em=0.14)
        top.addWidget(self._status)
        top.addStretch(1)
        self._clock = label("00:00", px=72)
        clock_font = self._clock.font()
        clock_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        self._clock.setFont(clock_font)
        top.addWidget(self._clock)
        rec.addLayout(top)
        self._wave = ThreadWave()
        rec.addWidget(self._wave)

        buttons = QHBoxLayout()
        buttons.setSpacing(14)
        self._start = PrimaryButton(_("Commencer l'enregistrement"), icon="mic")
        self._start.clicked.connect(self._start_recording)
        self._pause = outline_button(_("Pause"), icon="pause", large=True)
        self._pause.clicked.connect(self._pause_recording)
        self._resume = outline_button(_("Reprendre"), icon="play", large=True)
        self._resume.clicked.connect(self._resume_recording)
        self._finish = PrimaryButton(_("Terminer"), icon="stop")
        self._finish.clicked.connect(self._finish_recording)
        self._restart = QPushButton(_("Recommencer"))
        self._restart.setObjectName("mutedLink")
        self._restart.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restart.clicked.connect(self._restart_recording)
        for button in (self._start, self._pause, self._resume, self._finish, self._restart):
            buttons.addWidget(button)
        buttons.addStretch(1)
        rec.addLayout(buttons)
        self._hint = label("", px=15, color=theme.MUTED, wrap=True)
        rec.addWidget(self._hint)
        box.addWidget(self._recorder)

        # Panneau de fin
        self._done = QWidget()
        done = QVBoxLayout(self._done)
        done.setContentsMargins(0, 0, 0, 0)
        done.setSpacing(12)
        done.addWidget(label(_("Merci !"), theme.SCRIPT, 72, color=theme.RED_TEXT))
        self._done_text = label("", theme.SERIF, 19, wrap=True)
        done.addWidget(self._done_text)
        again = QHBoxLayout()
        again.setSpacing(24)
        new = PrimaryButton(_("Nouvelle interview"), icon="mic")
        new.clicked.connect(self._new_interview)
        again.addWidget(new)
        back = link_button(_("Retour à ma quête"))
        back.clicked.connect(self.back_to_quest)
        again.addWidget(back)
        again.addStretch(1)
        done.addSpacing(8)
        done.addLayout(again)
        self._done.hide()
        box.addWidget(self._done)
        return card

    def _fill_aside(self) -> None:
        clear_layout(self._aside)
        if self._track is None:
            return

        dig = QFrame()
        dig.setObjectName("softCard")
        dig_box = QVBoxLayout(dig)
        dig_box.setContentsMargins(28, 28, 28, 24)
        dig_box.setSpacing(12)
        dig_box.addWidget(label(_("Pour creuser"), theme.SCRIPT, 48, color=theme.LEAF_TEXT))
        for text in self._quest.follow_ups(self._track.question.id):
            line = QHBoxLayout()
            line.setSpacing(12)
            line.addWidget(LeafBullet(), 0, Qt.AlignmentFlag.AlignTop)
            line.addWidget(label(text, theme.SERIF, 18, italic=True, wrap=True), 1)
            dig_box.addLayout(line)
        self._aside.addWidget(dig)

        tips = QFrame()
        tips.setObjectName("plainCard")
        tips_box = QVBoxLayout(tips)
        tips_box.setContentsMargins(26, 22, 26, 22)
        tips_box.setSpacing(10)
        tips_box.addWidget(eyebrow(_("Conseils d'écoute"), color=theme.INK_SOFT))
        for tip in LISTENING_TIPS:
            tips_box.addWidget(label(_(tip), theme.SERIF, 17, wrap=True))
        self._aside.addWidget(tips)

        others = QVBoxLayout()
        others.setSpacing(0)
        others.addWidget(section_title(_("D'autres pistes")))
        others.addSpacing(6)
        for track in self._quest.other_tracks(self._track.question.id):
            row = ClickableFrame("row")
            row.setMinimumHeight(68)
            row.setEnabled(self._recording.state is RecordingState.IDLE)
            cell = QVBoxLayout(row)
            cell.setContentsMargins(8, 10, 8, 10)
            cell.setSpacing(2)
            cell.addWidget(eyebrow(track.theme.label, spacing_em=0.12))
            cell.addWidget(label(track.question.text, theme.SERIF, 18, wrap=True))
            question_id = track.question.id
            row.clicked.connect(lambda question_id=question_id: self._choose(question_id))
            others.addWidget(row)
        self._aside.addLayout(others)
        self._aside.addStretch(1)

    # Piste et personne

    def open(self, question_id: int | None = None, person_id: int | None = None) -> None:
        """Prépare l'écran pour une question et une personne (ou les suivantes proposées)."""
        if self.is_recording():
            return
        track = self._quest.track(question_id) if question_id is not None else None
        self._track = track or self._track or self._quest.next_track(self._skipped)
        self._fill_people(person_id)
        self._show_track()
        self._show_recorder()

    def _fill_people(self, person_id: int | None) -> None:
        current = person_id if person_id is not None else self._person.currentData()
        self._person.blockSignals(True)
        self._person.clear()
        for person in self._quest.people():
            self._person.addItem(person.display_name, person.id)
        index = self._person.findData(current)
        self._person.setCurrentIndex(max(index, 0))
        self._person.blockSignals(False)
        self._person_changed()

    def _show_track(self) -> None:
        if self._track is None:
            self._eyebrow.setText("")
            self._question.setText(_("Toutes les pistes ont été explorées."))
        else:
            self._eyebrow.setText(
                _("{track} · Piste en cours").format(track=self._track.theme.label).upper()
            )
            self._question.setText(self._track.question.text)
        self._fill_aside()
        self._update_state()

    def _person_changed(self) -> None:
        name = self._person.currentText()
        self._consent.set_text(consent_statement(name) if name else "")
        self._consent.set_checked(False)  # l'accord se donne à chaque fois, pour chaque personne
        self._update_state()

    def _change_question(self) -> None:
        if self._track is not None:
            self._skipped.add(self._track.question.id)
        self._track = self._quest.next_track(self._skipped)
        self._show_track()

    def _choose(self, question_id: int) -> None:
        self._track = self._quest.track(question_id)
        self._show_track()

    # Enregistrement

    def is_recording(self) -> bool:
        return self._recording.state is not RecordingState.IDLE

    def abandon(self) -> None:
        """Arrête et efface la prise en cours (quitter l'écran, fermer l'application)."""
        self._recording.discard()
        self._timer.stop()
        self._wave.reset()
        self._update_state()

    def _start_recording(self) -> None:
        person_id = self._person.currentData()
        if self._track is None or person_id is None or not self._consent.is_checked():
            return
        try:
            self._recording.start(
                person_id, self._track.question.id, consent_statement(self._person.currentText())
            )
        except RecordingError as error:
            self._hint.setText(str(error))
            self._hint.setStyleSheet(f"color: {theme.RED_TEXT};")
            return
        self._wave.reset()
        self._timer.start()
        self._update_state()

    def _pause_recording(self) -> None:
        self._recording.pause()
        self._update_state()

    def _resume_recording(self) -> None:
        self._recording.resume()
        self._update_state()

    def _finish_recording(self) -> None:
        self._timer.stop()
        try:
            story = self._recording.finish()
        except RecordingError as error:
            self._wave.reset()
            self._update_state(message=str(error))
            return
        name = self._person.currentText()
        self._done_text.setText(
            _(
                "Le récit de {name} ({duration}) est gardé sur cet ordinateur. Son texte se "
                "prépare ici même, sans rien envoyer en ligne : tu peux suivre l'avancement "
                "en bas de la fenêtre."
            ).format(name=name, duration=format_duration(story.duration_s))
        )
        self._recorder.hide()
        self._done.show()
        self._update_state()
        self.story_saved.emit(story.id)

    def _restart_recording(self) -> None:
        if not self.confirm(_("Effacer cet enregistrement et recommencer ?")):
            return
        self.abandon()

    def _new_interview(self) -> None:
        if self._track is not None:
            self._skipped.add(self._track.question.id)
        self._track = None
        self.open()

    def _show_recorder(self) -> None:
        self._done.hide()
        self._recorder.show()
        self._wave.reset()
        self._clock.setText("00:00")

    def confirm(self, question: str) -> bool:
        """Demande une confirmation (remplacée dans les tests)."""
        answer = QMessageBox.question(self, "Au fil d'une vie", question)
        return answer == QMessageBox.StandardButton.Yes

    def _tick(self) -> None:
        if self._recording.state is RecordingState.RECORDING:
            self._wave.commit()
        self._clock.setText(format_clock(self._recording.elapsed_s))

    def _update_state(self, message: str | None = None) -> None:
        state = self._recording.state
        idle = state is RecordingState.IDLE
        ready = idle and self._track is not None and self._person.count() > 0

        self._dot.filled = state is RecordingState.RECORDING
        self._dot.update()
        self._status.setText(
            {"idle": _("Prêt"), "recording": _("En cours"), "paused": _("En pause")}[
                state.value
            ].upper()
        )
        self._start.setVisible(idle)
        self._start.setEnabled(ready and self._consent.is_checked())
        self._pause.setVisible(state is RecordingState.RECORDING)
        self._resume.setVisible(state is RecordingState.PAUSED)
        self._finish.setVisible(not idle)
        self._restart.setVisible(not idle)
        if idle:
            self._clock.setText("00:00")

        for widget in (self._person, self._change, self._consent, self._add_person):
            widget.setEnabled(idle)
        for row in self.findChildren(ClickableFrame):
            row.setEnabled(idle)

        if message:
            self._hint.setStyleSheet(f"color: {theme.RED_TEXT};")
            self._hint.setText(message)
        elif not idle:
            self._hint.setText("")
        else:
            self._hint.setStyleSheet(f"color: {theme.MUTED};")
            if self._person.count() == 0:
                self._hint.setText(_("Ajoute d'abord un proche à interroger."))
            elif not self._consent.is_checked():
                self._hint.setText(_("Coche l'accord de la personne pour commencer."))
            else:
                self._hint.setText("")
