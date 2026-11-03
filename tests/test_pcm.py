from array import array

from au_fil_d_une_vie.services.pcm import PcmConverter, Resampler, SampleFormat, decode, to_mono


def _int16(values: list[int]) -> bytes:
    return array("h", values).tobytes()


def test_decodage_des_formats() -> None:
    assert decode(_int16([0, 1000, -1000]), SampleFormat.INT16) == [0, 1000, -1000]
    assert decode(bytes([128, 255, 0]), SampleFormat.UINT8) == [0, 127 << 8, -128 << 8]
    assert decode(array("i", [65536 * 1000]).tobytes(), SampleFormat.INT32) == [1000]
    assert decode(array("f", [0.5, -2.0]).tobytes(), SampleFormat.FLOAT) == [16383, -32768]


def test_un_octet_en_trop_est_ignore() -> None:
    assert decode(_int16([5]) + b"\x01", SampleFormat.INT16) == [5]


def test_passage_en_mono() -> None:
    assert to_mono([100, 300, -50, 50], channels=2) == [200, 0]
    assert to_mono([1, 2, 3], channels=1) == [1, 2, 3]


def test_48_khz_vers_16_khz() -> None:
    resampler = Resampler(48_000)
    sortie = resampler.process([3, 3, 3] * 100)
    assert sortie == [3] * 100


def test_le_reechantillonnage_se_poursuit_entre_les_morceaux() -> None:
    resampler = Resampler(44_100)
    total = sum(len(resampler.process([0] * 441)) for _ in range(100))  # 1 seconde
    assert abs(total - 16_000) <= 1


def test_chaine_complete_stereo_flottant_48_khz() -> None:
    converter = PcmConverter(SampleFormat.FLOAT, channels=2, rate=48_000)
    entree = array("f", [0.25, 0.25] * 4800).tobytes()  # 0,1 s
    sortie = array("h")
    sortie.frombytes(converter.convert(entree))
    assert len(sortie) == 1600
    assert set(sortie) == {8191}


def test_aucune_conversion_si_le_format_est_deja_bon() -> None:
    converter = PcmConverter(SampleFormat.INT16, channels=1, rate=16_000)
    assert converter.passthrough
    assert converter.convert(b"\x01\x02") == b"\x01\x02"
