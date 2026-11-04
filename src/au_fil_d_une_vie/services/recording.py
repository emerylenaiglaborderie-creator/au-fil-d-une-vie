"""Enregistrement d'une interview en WAV 16 kHz mono, avec le consentement du proche.

Le micro est derrière l'interface `AudioInput` : l'adaptateur Qt (`qt_audio.py`)
en production, un faux micro dans les tests.
"""

import math
import uuid
import wave
from array import array
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.models import Story
from au_fil_d_une_vie.repositories import StoryRepository

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2  # octets, PCM signé 16 bits
CHANNELS = 1
MIN_DURATION_S = 1.0

ChunkCallback = Callable[[bytes], None]
LevelCallback = Callable[[float], None]


class AudioInput(Protocol):
    """Source audio qui livre du PCM 16 bits mono à 16 kHz, par morceaux."""

    def start(self, on_chunk: ChunkCallback) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...


class RecordingState(StrEnum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"


class RecordingError(Exception):
    """Enregistrement impossible (micro absent, refusé, trop court...)."""


def consent_statement(person_name: str) -> str:
    """Texte exact accepté avant l'enregistrement, conservé avec le récit."""
    return _(
        "{name} sait que la conversation est enregistrée et est d'accord "
        "pour que son récit soit gardé dans l'application."
    ).format(name=person_name)


def rms_level(chunk: bytes) -> float:
    """Niveau sonore d'un morceau, entre 0 et 1 (échelle racine, plus lisible)."""
    samples = array("h")
    samples.frombytes(chunk[: len(chunk) - len(chunk) % SAMPLE_WIDTH])
    if not samples:
        return 0.0
    mean_square = sum(s * s for s in samples) / len(samples)
    return min(1.0, math.sqrt(math.sqrt(mean_square) / 32768))


class RecordingService:
    """Une prise à la fois : démarrer, mettre en pause, terminer ou recommencer."""

    def __init__(
        self,
        stories: StoryRepository,
        audio_dir: Path,
        input_factory: Callable[[], AudioInput],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._stories = stories
        self._audio_dir = audio_dir
        self._input_factory = input_factory
        self._clock = clock
        self._state = RecordingState.IDLE
        self._input: AudioInput | None = None
        self._wav: wave.Wave_write | None = None
        self._path: Path | None = None
        self._frames = 0
        self._started_at: datetime | None = None
        self._take: tuple[int, int, str] | None = None
        self.on_level: LevelCallback | None = None

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def elapsed_s(self) -> float:
        return self._frames / SAMPLE_RATE

    def start(self, person_id: int, question_id: int, consent: str) -> None:
        """Démarre une prise. Le consentement du proche est exigé avant tout."""
        if self._state is not RecordingState.IDLE:
            raise RecordingError(_("Un enregistrement est déjà en cours."))
        if not consent.strip():
            raise RecordingError(_("Le consentement du proche est obligatoire."))
        self._started_at = self._clock()
        stamp = self._started_at.strftime("%Y%m%d-%H%M%S")
        relative = (
            Path(self._started_at.strftime("%Y-%m")) / f"recit-{stamp}-{uuid.uuid4().hex[:6]}.wav"
        )
        self._path = self._audio_dir / relative
        self._path.parent.mkdir(parents=True, exist_ok=True)
        wav = wave.open(str(self._path), "wb")  # noqa: SIM115 (fermé dans _close)
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(SAMPLE_RATE)
        self._wav = wav
        self._frames = 0
        self._take = (person_id, question_id, consent)
        self._input = self._input_factory()
        self._state = RecordingState.RECORDING
        try:
            self._input.start(self._on_chunk)
        except Exception as error:
            self.discard()
            raise RecordingError(str(error)) from error

    def pause(self) -> None:
        if self._state is RecordingState.RECORDING and self._input:
            self._input.pause()
            self._state = RecordingState.PAUSED

    def resume(self) -> None:
        if self._state is RecordingState.PAUSED and self._input:
            self._input.resume()
            self._state = RecordingState.RECORDING

    def finish(self) -> Story:
        """Arrête la prise et crée le récit (avec son consentement) dans la base."""
        if self._state is RecordingState.IDLE or self._take is None or self._path is None:
            raise RecordingError(_("Aucun enregistrement en cours."))
        duration = self.elapsed_s
        person_id, question_id, consent = self._take
        path = self._path
        started_at = self._started_at
        self._close()
        if duration < MIN_DURATION_S:
            path.unlink(missing_ok=True)
            raise RecordingError(_("L'enregistrement est trop court."))
        return self._stories.create(
            person_id=person_id,
            question_id=question_id,
            duration_s=round(duration, 2),
            audio_path=path.relative_to(self._audio_dir),
            consent_statement=consent,
            recorded_at=started_at,
        )

    def discard(self) -> None:
        """Abandonne la prise en cours (« Recommencer ») : rien n'est gardé."""
        path = self._path
        self._close()
        if path is not None:
            path.unlink(missing_ok=True)

    def _on_chunk(self, chunk: bytes) -> None:
        if self._state is not RecordingState.RECORDING or self._wav is None:
            return
        self._wav.writeframes(chunk)
        self._frames += len(chunk) // (SAMPLE_WIDTH * CHANNELS)
        if self.on_level is not None:
            self.on_level(rms_level(chunk))

    def _close(self) -> None:
        if self._input is not None:
            self._input.stop()
        if self._wav is not None:
            self._wav.close()
        self._input = None
        self._wav = None
        self._path = None
        self._take = None
        self._started_at = None
        self._state = RecordingState.IDLE
