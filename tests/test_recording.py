import math
import sqlite3
import wave
from array import array
from datetime import UTC, datetime
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import StoryRepository
from au_fil_d_une_vie.services.fake_audio import FakeAudioInput
from au_fil_d_une_vie.services.recording import (
    SAMPLE_RATE,
    RecordingError,
    RecordingService,
    RecordingState,
    consent_statement,
    rms_level,
)
from tests.conftest import Scene


def _silence(seconds: float) -> bytes:
    return bytes(int(SAMPLE_RATE * seconds) * 2)


def _sinus(seconds: float, amplitude: int = 12_000) -> bytes:
    n = int(SAMPLE_RATE * seconds)
    return array(
        "h", (int(amplitude * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)) for i in range(n))
    ).tobytes()


@pytest.fixture
def micro() -> FakeAudioInput:
    return FakeAudioInput()


@pytest.fixture
def service(conn: sqlite3.Connection, tmp_path: Path, micro: FakeAudioInput) -> RecordingService:
    return RecordingService(
        StoryRepository(conn),
        tmp_path / "audio",
        lambda: micro,
        clock=lambda: datetime(2026, 11, 3, 18, 45, tzinfo=UTC),
    )


def test_enregistrer_un_recit(
    service: RecordingService,
    micro: FakeAudioInput,
    scene: Scene,
    tmp_path: Path,
    conn: sqlite3.Connection,
) -> None:
    accord = consent_statement("Mamie Yvonne")
    service.start(scene.yvonne.id, scene.q_ecole.id, accord)
    assert service.state is RecordingState.RECORDING
    micro.hear(_sinus(1.5))
    assert service.elapsed_s == pytest.approx(1.5)

    recit = service.finish()

    assert service.state is RecordingState.IDLE and micro.stopped
    assert recit.duration_s == pytest.approx(1.5)
    assert recit.audio_path.parts[0] == "2026-11"
    fichier = tmp_path / "audio" / recit.audio_path
    with wave.open(str(fichier), "rb") as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (SAMPLE_RATE, 1, 2)
        assert wav.getnframes() == int(1.5 * SAMPLE_RATE)
    consentement = StoryRepository(conn).consent_for(recit.id)
    assert consentement is not None and consentement.statement == accord


def test_pas_d_enregistrement_sans_consentement(service: RecordingService, scene: Scene) -> None:
    with pytest.raises(RecordingError):
        service.start(scene.yvonne.id, scene.q_ecole.id, "  ")
    assert service.state is RecordingState.IDLE


def test_la_pause_n_enregistre_rien(
    service: RecordingService, micro: FakeAudioInput, scene: Scene
) -> None:
    service.start(scene.yvonne.id, scene.q_ecole.id, "accord")
    micro.hear(_silence(1.0))
    service.pause()
    assert micro.paused and service.state is RecordingState.PAUSED
    micro.hear(_silence(5.0))  # morceau arrivé en retard : ignoré
    service.resume()
    micro.hear(_silence(1.0))
    assert service.elapsed_s == pytest.approx(2.0)


def test_recommencer_efface_la_prise(
    service: RecordingService,
    micro: FakeAudioInput,
    scene: Scene,
    tmp_path: Path,
    conn: sqlite3.Connection,
) -> None:
    service.start(scene.yvonne.id, scene.q_ecole.id, "accord")
    micro.hear(_silence(2.0))
    service.discard()
    assert list((tmp_path / "audio").rglob("*.wav")) == []
    assert StoryRepository(conn).list_all(include_hidden=True) == []


def test_un_enregistrement_trop_court_n_est_pas_garde(
    service: RecordingService, micro: FakeAudioInput, scene: Scene, tmp_path: Path
) -> None:
    service.start(scene.yvonne.id, scene.q_ecole.id, "accord")
    micro.hear(_silence(0.3))
    with pytest.raises(RecordingError):
        service.finish()
    assert list((tmp_path / "audio").rglob("*.wav")) == []


def test_une_seule_prise_a_la_fois(service: RecordingService, scene: Scene) -> None:
    service.start(scene.yvonne.id, scene.q_ecole.id, "accord")
    with pytest.raises(RecordingError):
        service.start(scene.papa.id, scene.q_ecole.id, "accord")


def test_le_niveau_sonore_est_transmis(
    service: RecordingService, micro: FakeAudioInput, scene: Scene
) -> None:
    niveaux: list[float] = []
    service.on_level = niveaux.append
    service.start(scene.yvonne.id, scene.q_ecole.id, "accord")
    micro.hear(_silence(0.1))
    micro.hear(_sinus(0.1))
    assert niveaux[0] == 0.0
    assert 0.3 < niveaux[1] <= 1.0


def test_niveau_d_un_morceau_vide() -> None:
    assert rms_level(b"") == 0.0
    assert rms_level(b"\x01") == 0.0


def test_le_consentement_ne_suppose_pas_le_genre() -> None:
    texte = consent_statement("Tonton Alain")
    assert texte.startswith("Tonton Alain sait que la conversation est enregistrée")
    assert "elle" not in texte.split() and "il" not in texte.split()
