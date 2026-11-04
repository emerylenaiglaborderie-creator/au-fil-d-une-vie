from pathlib import Path

from au_fil_d_une_vie.services.whisper import WhisperModels


def test_un_modele_est_installe_quand_son_fichier_existe(tmp_path: Path) -> None:
    modeles = WhisperModels(tmp_path)
    assert not modeles.is_installed("small")
    modeles.path("small").mkdir(parents=True)
    (modeles.path("small") / "model.bin").write_bytes(b"")
    assert modeles.is_installed("small")
    assert not modeles.is_installed("base")


def test_lecture_d_un_wav_de_l_application(tmp_path: Path) -> None:
    import wave
    from array import array

    import pytest

    from au_fil_d_une_vie.services.whisper import read_wav

    chemin = tmp_path / "a.wav"
    with wave.open(str(chemin), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(array("h", [0, 16384, -32768]).tobytes())
    assert read_wav(chemin).tolist() == [0.0, 0.5, -1.0]

    autre = tmp_path / "b.wav"
    with wave.open(str(autre), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(44_100)
        wav.writeframes(b"\x00" * 8)
    with pytest.raises(ValueError):
        read_wav(autre)
