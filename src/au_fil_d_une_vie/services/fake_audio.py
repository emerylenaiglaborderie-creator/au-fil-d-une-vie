"""Micro factice : utilisé par les tests et les captures d'écran, jamais en vrai."""

import math
from array import array

from au_fil_d_une_vie.services.recording import SAMPLE_RATE, ChunkCallback


class FakeAudioInput:
    """On lui fait « entendre » des morceaux à la main avec `hear`."""

    def __init__(self) -> None:
        self.callback: ChunkCallback | None = None
        self.paused = False
        self.stopped = False

    def start(self, on_chunk: ChunkCallback) -> None:
        self.callback = on_chunk
        self.stopped = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.stopped = True

    def hear(self, chunk: bytes) -> None:
        if self.callback is not None:
            self.callback(chunk)


def tone(seconds: float, amplitude: int = 12_000, frequency: float = 220.0) -> bytes:
    """Son de test (sinusoïde) en PCM 16 bits mono 16 kHz."""
    n = int(SAMPLE_RATE * seconds)
    return array(
        "h",
        (int(amplitude * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(n)),
    ).tobytes()
