"""Lecteur audio d'un récit : bouton rond, progression en fil, vitesse de lecture."""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QWidget

from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.text import clock
from au_fil_d_une_vie.ui.widgets import icon_pixmap, label, outline_button, paint_dot, soft_shadow

SPEEDS = (1.0, 1.25, 1.5, 0.75)


class RoundPlayButton(QAbstractButton):
    """Bouton rouge rond en relief, lecture ou pause."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(56, 59)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.playing = False
        self._play = icon_pixmap("play", 22)
        self._pause = icon_pixmap("pause", 22)
        self.setAccessibleName("Lecture")

    def sizeHint(self) -> QSize:
        return QSize(56, 59)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pressed = self.isDown()
        enabled = self.isEnabled()
        offset = 2 if pressed else 0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.color(theme.RED_SHADOW if enabled else theme.BORDER))
        painter.drawEllipse(QRectF(0, 3, 56, 56))
        painter.setBrush(theme.color(theme.RED if enabled else theme.LEAF_BORDER))
        painter.drawEllipse(QRectF(0, offset, 56, 56))
        icon = self._pause if self.playing else self._play
        painter.drawPixmap(QPointF(17 + (0 if self.playing else 1), 17 + offset), icon)


class SeekBar(QWidget):
    """Progression en fil : trait d'encre jusqu'au point rouge, qu'on peut faire glisser."""

    seek_requested = Signal(float)  # fraction entre 0 et 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fraction = 0.0

    def set_fraction(self, fraction: float) -> None:
        self._fraction = max(0.0, min(1.0, fraction))
        self.update()

    def _fraction_at(self, x: float) -> float:
        return max(0.0, min(1.0, (x - 8) / max(1, self.width() - 16)))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.seek_requested.emit(self._fraction_at(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.seek_requested.emit(self._fraction_at(event.position().x()))

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        mid = self.height() / 2
        left, right = 8.0, self.width() - 8.0
        x = left + (right - left) * self._fraction
        track = QPen(theme.color("#D8DCCB"), 3)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        played = QPen(theme.color(theme.THREAD), 3)
        played.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawLine(QPointF(left, mid), QPointF(right, mid))
        painter.setPen(played)
        painter.drawLine(QPointF(left, mid), QPointF(x, mid))
        paint_dot(painter, QPointF(x, mid - 1), 16, filled=True)


class AudioPlayer(QFrame):
    """Carte de lecture. Le moteur Qt n'est créé qu'à la première lecture."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playerCard")
        soft_shadow(self, blur=28, dy=10, alpha=20)
        row = QHBoxLayout(self)
        row.setContentsMargins(24, 16, 24, 16)
        row.setSpacing(20)
        self._button = RoundPlayButton()
        self._button.clicked.connect(self.toggle)
        row.addWidget(self._button)
        self._position = label("00:00", px=16, weight=QFont.Weight.DemiBold)
        row.addWidget(self._position)
        self._seek = SeekBar()
        self._seek.seek_requested.connect(self._seek_to)
        row.addWidget(self._seek, 1)
        self._total = label("00:00", px=16, color=theme.MUTED)
        row.addWidget(self._total)
        self._speed = outline_button("1×")
        self._speed.setMinimumWidth(56)
        self._speed.setAccessibleName("Vitesse de lecture")
        self._speed.clicked.connect(self._next_speed)
        row.addWidget(self._speed)
        self._missing = label("", px=14, color=theme.MUTED)
        self._missing.hide()
        row.addWidget(self._missing)

        self._path: Path | None = None
        self._duration_ms = 0
        self._speed_index = 0
        self._player: QMediaPlayer | None = None  # créé à la première lecture
        self._output: QAudioOutput | None = None

    def set_source(self, path: Path, duration_s: float) -> None:
        self.stop()
        self._path = path
        self._duration_ms = int(duration_s * 1000)
        self._total.setText(clock(duration_s))
        self._position.setText("00:00")
        self._seek.set_fraction(0)
        available = path.is_file()
        for widget in (self._button, self._seek, self._speed):
            widget.setEnabled(available)
        self._missing.setVisible(not available)
        self._missing.setText("" if available else "Pas d'enregistrement pour ce récit.")
        if self._player is not None and available:
            self._player.setSource(QUrl.fromLocalFile(str(path)))

    def _ensure_player(self) -> QMediaPlayer:
        if self._player is None:
            self._output = QAudioOutput(self)
            player = QMediaPlayer(self)
            player.setAudioOutput(self._output)
            player.positionChanged.connect(self._on_position)
            player.durationChanged.connect(self._on_duration)
            player.playbackStateChanged.connect(self._on_state)
            if self._path is not None:
                player.setSource(QUrl.fromLocalFile(str(self._path)))
            self._player = player
        return self._player

    def toggle(self) -> None:
        player = self._ensure_player()
        if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            player.pause()
        else:
            player.setPlaybackRate(SPEEDS[self._speed_index])
            player.play()

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()

    def _seek_to(self, fraction: float) -> None:
        self._seek.set_fraction(fraction)
        position = int(fraction * self._duration_ms)
        self._position.setText(clock(position / 1000))
        if self._path is not None and self._path.is_file():
            self._ensure_player().setPosition(position)

    def _next_speed(self) -> None:
        self._speed_index = (self._speed_index + 1) % len(SPEEDS)
        speed = SPEEDS[self._speed_index]
        self._speed.setText(f"{speed:g}×".replace(".", ","))
        if self._player is not None:
            self._player.setPlaybackRate(speed)

    def _on_position(self, position: int) -> None:
        self._position.setText(clock(position / 1000))
        if self._duration_ms:
            self._seek.set_fraction(position / self._duration_ms)

    def _on_duration(self, duration: int) -> None:
        if duration > 0:
            self._duration_ms = duration
            self._total.setText(clock(duration / 1000))

    def _on_state(self, state: QMediaPlayer.PlaybackState) -> None:
        self._button.playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._button.setAccessibleName("Pause" if self._button.playing else "Lecture")
        self._button.update()
