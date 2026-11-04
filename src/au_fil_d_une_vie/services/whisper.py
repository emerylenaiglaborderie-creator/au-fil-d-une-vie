"""Transcription locale avec faster-whisper, et gestion du modèle téléchargé.

Le modèle est chargé avec `local_files_only=True` : la transcription ne touche
jamais au réseau. Le seul téléchargement possible est `WhisperModels.download`,
lancé explicitement par l'utilisateur.
"""

import wave
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from au_fil_d_une_vie.services.recording import CHANNELS, SAMPLE_RATE, SAMPLE_WIDTH
from au_fil_d_une_vie.services.transcription import ProgressCallback, TranscriptionResult

DEFAULT_SIZE = "small"
FALLBACK_SIZE = "base"
APPROX_SIZE_MB = {"tiny": 75, "base": 145, "small": 465}
LANGUAGE = "fr"


def read_wav(path: Path) -> NDArray[np.float32]:
    """Lit un WAV de l'application (16 kHz, mono, 16 bits) en échantillons entre -1 et 1.

    On décode nous-mêmes plutôt que de passer par PyAV : nos fichiers ont toujours
    ce format, et cela évite une dépendance fragile.
    """
    with wave.open(str(path), "rb") as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (
            SAMPLE_RATE,
            CHANNELS,
            SAMPLE_WIDTH,
        ):
            raise ValueError(f"{path.name} n'est pas un WAV 16 kHz mono 16 bits.")
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0


class WhisperModels:
    """Modèles Whisper rangés dans le dossier de données (un sous-dossier par taille)."""

    def __init__(self, models_dir: Path) -> None:
        self._dir = models_dir

    def path(self, size: str) -> Path:
        return self._dir / f"whisper-{size}"

    def is_installed(self, size: str) -> bool:
        return (self.path(size) / "model.bin").is_file()

    def download(self, size: str) -> Path:
        """Télécharge le modèle (seule opération réseau de l'application)."""
        from faster_whisper.utils import download_model

        target = self.path(size)
        target.mkdir(parents=True, exist_ok=True)
        download_model(size, output_dir=str(target))
        return target


class FasterWhisperTranscriber:
    """Adaptateur `Transcriber` : faster-whisper sur le processeur (int8)."""

    def __init__(self, model_path: Path, cpu_threads: int = 0) -> None:
        self._model_path = model_path
        self._cpu_threads = cpu_threads
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                str(self._model_path),
                device="cpu",
                compute_type="int8",
                cpu_threads=self._cpu_threads,
                local_files_only=True,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        on_progress: ProgressCallback | None = None,
        hotwords: str | None = None,
        language: str = LANGUAGE,
    ) -> TranscriptionResult:
        segments, info = self._load().transcribe(
            read_wav(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,
            # Plus fiable qu'un prompt pour les noms propres (« Le Gall » plutôt que « Legalle »).
            hotwords=hotwords,
        )
        duration = float(info.duration) or 1.0
        parts: list[str] = []
        for segment in segments:  # générateur : le calcul se fait ici, segment par segment
            parts.append(segment.text.strip())
            if on_progress is not None:
                on_progress(min(1.0, float(segment.end) / duration))
        if on_progress is not None:
            on_progress(1.0)
        return TranscriptionResult(
            text=" ".join(p for p in parts if p), language=language, duration_s=duration
        )
