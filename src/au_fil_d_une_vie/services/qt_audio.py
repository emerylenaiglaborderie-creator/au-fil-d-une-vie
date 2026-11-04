"""Adaptateur micro basé sur QtMultimedia (QAudioSource)."""

from PySide6.QtCore import QIODevice
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource, QMediaDevices, QtAudio

from au_fil_d_une_vie.services.pcm import PcmConverter, SampleFormat
from au_fil_d_une_vie.services.recording import (
    CHANNELS,
    SAMPLE_RATE,
    ChunkCallback,
    RecordingError,
)

_FORMATS = {
    QAudioFormat.SampleFormat.UInt8: SampleFormat.UINT8,
    QAudioFormat.SampleFormat.Int16: SampleFormat.INT16,
    QAudioFormat.SampleFormat.Int32: SampleFormat.INT32,
    QAudioFormat.SampleFormat.Float: SampleFormat.FLOAT,
}

MIC_HELP = (
    "Vérifie qu'un micro est branché et que l'application a le droit de l'utiliser "
    "(sur Mac : Réglages Système, Confidentialité et sécurité, Micro)."
)


def _wanted_format() -> QAudioFormat:
    fmt = QAudioFormat()
    fmt.setSampleRate(SAMPLE_RATE)
    fmt.setChannelCount(CHANNELS)
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return fmt


class QtAudioInput:
    """Micro par défaut du système, converti en 16 kHz mono si besoin."""

    def __init__(self, device: QAudioDevice | None = None) -> None:
        self._device = device or QMediaDevices.defaultAudioInput()
        self._source: QAudioSource | None = None
        self._io: QIODevice | None = None

    def start(self, on_chunk: ChunkCallback) -> None:
        if self._device.isNull():
            raise RecordingError("Aucun micro n'a été trouvé. " + MIC_HELP)
        fmt = _wanted_format()
        if not self._device.isFormatSupported(fmt):
            fmt = self._device.preferredFormat()
        sample_format = _FORMATS.get(fmt.sampleFormat())
        if sample_format is None:
            raise RecordingError("Le format du micro n'est pas pris en charge.")
        converter = PcmConverter(sample_format, fmt.channelCount(), fmt.sampleRate())

        self._source = QAudioSource(self._device, fmt)
        io = self._source.start()
        if io is None or self._source.error() != QtAudio.Error.NoError:
            self.stop()
            raise RecordingError("Le micro n'a pas pu démarrer. " + MIC_HELP)
        self._io = io

        def read() -> None:
            data = io.readAll().data()
            if data:
                on_chunk(converter.convert(bytes(data)))

        io.readyRead.connect(read)

    def pause(self) -> None:
        if self._source is not None:
            self._source.suspend()

    def resume(self) -> None:
        if self._source is not None:
            self._source.resume()

    def stop(self) -> None:
        if self._source is not None:
            self._source.stop()
        self._source = None
        self._io = None
