from pathlib import Path

from au_fil_d_une_vie import config


def test_les_chemins_sont_sous_le_dossier_de_donnees() -> None:
    racine = config.data_dir()
    assert isinstance(racine, Path)
    for chemin in (config.db_path(), config.audio_dir(), config.models_dir()):
        assert chemin.parent == racine
