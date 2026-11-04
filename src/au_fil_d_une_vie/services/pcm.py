"""Conversion de PCM brut vers du 16 bits mono à 16 kHz.

Beaucoup de micros ne proposent que 44,1 ou 48 kHz, en stéréo ou en flottant :
on convertit au fil de l'eau, morceau par morceau.
"""

from array import array
from enum import StrEnum

from au_fil_d_une_vie.services.recording import SAMPLE_RATE


class SampleFormat(StrEnum):
    UINT8 = "uint8"
    INT16 = "int16"
    INT32 = "int32"
    FLOAT = "float"


_BYTES = {
    SampleFormat.UINT8: 1,
    SampleFormat.INT16: 2,
    SampleFormat.INT32: 4,
    SampleFormat.FLOAT: 4,
}


def decode(chunk: bytes, sample_format: SampleFormat) -> list[int]:
    """Échantillons entiers 16 bits, tous canaux confondus (entrelacés)."""
    width = _BYTES[sample_format]
    data = chunk[: len(chunk) - len(chunk) % width]
    if sample_format is SampleFormat.UINT8:
        return [(b - 128) << 8 for b in data]
    if sample_format is SampleFormat.INT16:
        samples = array("h")
        samples.frombytes(data)
        return samples.tolist()
    if sample_format is SampleFormat.INT32:
        wide = array("i")
        wide.frombytes(data)
        return [s >> 16 for s in wide]
    floats = array("f")
    floats.frombytes(data)
    return [max(-32768, min(32767, int(f * 32767))) for f in floats]


def to_mono(samples: list[int], channels: int) -> list[int]:
    if channels <= 1:
        return samples
    usable = len(samples) - len(samples) % channels
    return [sum(samples[i : i + channels]) // channels for i in range(0, usable, channels)]


class Resampler:
    """Rééchantillonnage par moyenne sur chaque fenêtre (filtre passe-bas simple)."""

    def __init__(self, rate_in: int, rate_out: int = SAMPLE_RATE) -> None:
        self._step = rate_in / rate_out
        self._buffer: list[int] = []
        self._pos = 0.0

    def process(self, samples: list[int]) -> list[int]:
        if self._step == 1.0:
            return samples
        self._buffer.extend(samples)
        out: list[int] = []
        while self._pos + self._step <= len(self._buffer):
            start = int(self._pos)
            end = max(start + 1, int(self._pos + self._step))
            window = self._buffer[start:end]
            out.append(sum(window) // len(window))
            self._pos += self._step
        consumed = int(self._pos)
        del self._buffer[:consumed]
        self._pos -= consumed
        return out


class PcmConverter:
    """Chaîne complète : décodage, passage en mono, rééchantillonnage, encodage."""

    def __init__(self, sample_format: SampleFormat, channels: int, rate: int) -> None:
        self._format = sample_format
        self._channels = channels
        self._resampler = Resampler(rate)
        self.passthrough = (
            sample_format is SampleFormat.INT16 and channels == 1 and rate == SAMPLE_RATE
        )

    def convert(self, chunk: bytes) -> bytes:
        if self.passthrough:
            return chunk
        mono = to_mono(decode(chunk, self._format), self._channels)
        return array("h", self._resampler.process(mono)).tobytes()
