"""Contrat de transcription, indépendant du moteur utilisé."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class TranscriptionResult:
    """Texte brut obtenu à partir d'un enregistrement."""

    text: str
    language: str
    duration_s: float


ProgressCallback = Callable[[float], None]
"""Reçoit l'avancement entre 0.0 et 1.0."""


class Transcriber(Protocol):
    """Moteur de transcription locale (adaptateur : FasterWhisperTranscriber)."""

    def transcribe(
        self,
        audio_path: Path,
        on_progress: ProgressCallback | None = None,
        hotwords: str | None = None,
        language: str = "fr",
    ) -> TranscriptionResult:
        """`hotwords` : noms propres à bien reconnaître ; `language` : langue parlée."""
        ...
