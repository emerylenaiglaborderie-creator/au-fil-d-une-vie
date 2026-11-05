"""Préparation de la synchronisation : UUID, journal des modifications et acquittements."""

import sqlite3
import uuid
from pathlib import Path

import pytest

from au_fil_d_une_vie.models import StoryStatus, SyncEntity, SyncOperation
from au_fil_d_une_vie.repositories import (
    KeywordCandidate,
    KeywordRepository,
    NoteRepository,
    PersonRepository,
    StoryRepository,
    SyncRepository,
    ThemeRepository,
    TranscriptRepository,
)
from au_fil_d_une_vie.repositories.database import _migrations, migrate, schema_version
from tests.conftest import CONSENT, Scene

SYNCED_TABLES = ("person", "theme", "question", "follow_up", "story")


def _uuid(conn: sqlite3.Connection, table: str, row_id: int) -> str:
    value: str = conn.execute(f"SELECT uuid FROM {table} WHERE id = ?", (row_id,)).fetchone()[0]
    return value


def _journal(conn: sqlite3.Connection) -> set[tuple[SyncEntity, str, SyncOperation]]:
    return {(c.entity, c.key, c.operation) for c in SyncRepository(conn).pending()}


def _tout_envoyer(conn: sqlite3.Connection) -> None:
    """Simule un envoi réussi de tout le journal (version 1 pour chaque donnée)."""
    sync = SyncRepository(conn)
    for change in sync.pending():
        sync.acknowledge(change, 1)


# Identifiants universels


def test_chaque_donnee_synchronisee_recoit_un_uuid(conn: sqlite3.Connection, scene: Scene) -> None:
    ThemeRepository(conn).add_follow_up(scene.q_ecole.id, "Tu y allais à pied ?")
    scene.story(conn, scene.yvonne, scene.q_ecole)
    for table in SYNCED_TABLES:
        valeurs = [row[0] for row in conn.execute(f"SELECT uuid FROM {table}")]
        assert valeurs, table
        for valeur in valeurs:
            assert uuid.UUID(valeur).version == 4


def test_une_ligne_sans_uuid_est_refusee(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="uuid obligatoire"):
        conn.execute(
            "INSERT INTO person (display_name, relationship, created_at) VALUES ('A', 'b', 'c')"
        )


def test_un_uuid_ne_se_modifie_pas(conn: sqlite3.Connection, scene: Scene) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="uuid non modifiable"):
        conn.execute("UPDATE person SET uuid = ? WHERE id = ?", (str(uuid.uuid4()), scene.papa.id))


def test_la_migration_donne_un_uuid_aux_donnees_existantes(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "ancienne.db")
    for version, script in _migrations():
        if version <= 3:
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;")
    conn.executescript(
        """
        INSERT INTO person (display_name, relationship, created_at)
        VALUES ('Mamie Yvonne', 'grand-mère', '2026-10-01T10:00:00+00:00'),
               ('Papa', 'père', '2026-10-01T10:00:00+00:00');
        INSERT INTO theme (slug, label, position) VALUES ('enfance', 'Enfance', 1);
        INSERT INTO question (theme_id, text, position) VALUES (1, 'Ton école ?', 1);
        INSERT INTO follow_up (question_id, text, position) VALUES (1, 'À pied ?', 1);
        INSERT INTO story (person_id, question_id, recorded_at, duration_s, audio_path)
        VALUES (1, 1, '2026-10-12T10:00:00+00:00', 252, 'a.wav');
        """
    )

    migrate(conn)

    assert schema_version(conn) == _migrations()[-1][0]
    for table in SYNCED_TABLES:
        valeurs = [row[0] for row in conn.execute(f"SELECT uuid FROM {table}")]
        assert all(uuid.UUID(v).version == 4 for v in valeurs), table
    personnes = [row[0] for row in conn.execute("SELECT uuid FROM person")]
    assert len(set(personnes)) == 2
    # Les données d'avant la migration n'ont pas encore été journalisées.
    assert conn.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()[0] == 0
    conn.close()


# Journal des modifications


def test_un_nouveau_recit_est_journalise(conn: sqlite3.Connection, scene: Scene) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    cle = _uuid(conn, "story", story.id)
    assert (SyncEntity.STORY, cle, SyncOperation.UPSERT) in _journal(conn)
    assert (SyncEntity.PERSON, _uuid(conn, "person", scene.yvonne.id), SyncOperation.UPSERT) in (
        _journal(conn)
    )


def test_une_donnee_modifiee_plusieurs_fois_n_a_qu_une_entree(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    people = PersonRepository(conn)
    people.rename(scene.papa.id, "Papa Jean", "père")
    people.rename(scene.papa.id, "Papa", "père")
    cle = _uuid(conn, "person", scene.papa.id)
    entrees = [c for c in SyncRepository(conn).pending() if c.key == cle]
    assert len(entrees) == 1


def test_le_statut_de_transcription_reste_local(conn: sqlite3.Connection, scene: Scene) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    _tout_envoyer(conn)
    StoryRepository(conn).set_status(story.id, StoryStatus.TRANSCRIBED)
    assert _journal(conn) == set()


def test_masquer_un_recit_est_journalise(conn: sqlite3.Connection, scene: Scene) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    _tout_envoyer(conn)
    StoryRepository(conn).set_hidden(story.id, True)
    assert _journal(conn) == {
        (SyncEntity.STORY, _uuid(conn, "story", story.id), SyncOperation.UPSERT)
    }


def test_le_texte_est_journalise_sous_l_uuid_du_recit(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    _tout_envoyer(conn)
    transcripts = TranscriptRepository(conn)
    transcripts.save_raw(story.id, "On allait à l'école en sabots.")
    transcripts.save_raw(story.id, "On allait à l'école en sabots, au bourg.")
    transcripts.save_book_text(story.id, "Nous allions à l'école en sabots.")
    assert _journal(conn) == {
        (SyncEntity.TRANSCRIPT, _uuid(conn, "story", story.id), SyncOperation.UPSERT)
    }


def test_seuls_les_mots_cles_valides_sont_journalises(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    _tout_envoyer(conn)
    keywords = KeywordRepository(conn)
    keywords.propose(story.id, [KeywordCandidate("sabot", "sabots", 0.8)])
    assert _journal(conn) == set()

    keyword_id = keywords.for_story(story.id)[0].keyword.id
    keywords.set_validated(story.id, keyword_id, True)
    cle = _uuid(conn, "story", story.id)
    assert _journal(conn) == {(SyncEntity.STORY_KEYWORDS, cle, SyncOperation.UPSERT)}

    _tout_envoyer(conn)
    keywords.remove(story.id, keyword_id)
    assert _journal(conn) == {(SyncEntity.STORY_KEYWORDS, cle, SyncOperation.UPSERT)}


# Suppressions


def test_une_donnee_jamais_envoyee_puis_supprimee_ne_laisse_rien(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    TranscriptRepository(conn).save_raw(story.id, "Texte")
    NoteRepository(conn).save(story.id, "Ce que j'en retiens")
    cle = _uuid(conn, "story", story.id)

    StoryRepository(conn).delete(story.id)

    assert all(c.key != cle for c in SyncRepository(conn).pending())


def test_un_recit_deja_envoye_laisse_une_pierre_tombale_sans_contenu(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    TranscriptRepository(conn).save_raw(story.id, "Texte confidentiel")
    _tout_envoyer(conn)
    cle = _uuid(conn, "story", story.id)
    NoteRepository(conn).save(story.id, "Note confidentielle")  # modifiée, pas encore envoyée

    StoryRepository(conn).delete(story.id)

    assert _journal(conn) == {(SyncEntity.STORY, cle, SyncOperation.DELETE)}
    contenu = " ".join(str(v) for row in conn.execute("SELECT * FROM sync_outbox") for v in row)
    assert "confidentiel" not in contenu


def test_supprimer_un_proche_journalise_aussi_ses_recits(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    _tout_envoyer(conn)
    cle_yvonne = _uuid(conn, "person", scene.yvonne.id)
    cle_recit = _uuid(conn, "story", story.id)

    PersonRepository(conn).delete(scene.yvonne.id)

    assert _journal(conn) == {
        (SyncEntity.PERSON, cle_yvonne, SyncOperation.DELETE),
        (SyncEntity.STORY, cle_recit, SyncOperation.DELETE),
    }


def test_vider_une_note_envoyee_la_supprime_sur_le_serveur(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    notes = NoteRepository(conn)
    notes.save(story.id, "À retenir")
    _tout_envoyer(conn)

    notes.save(story.id, "   ")

    assert _journal(conn) == {
        (SyncEntity.NOTE, _uuid(conn, "story", story.id), SyncOperation.DELETE)
    }


def test_vider_une_note_jamais_envoyee_ne_laisse_rien(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    story = scene.story(conn, scene.yvonne, scene.q_ecole)
    _tout_envoyer(conn)
    notes = NoteRepository(conn)
    notes.save(story.id, "À retenir")
    notes.save(story.id, "")
    assert _journal(conn) == set()


# Acquittement et réception


def test_l_acquittement_retient_la_version_du_serveur(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    sync = SyncRepository(conn)
    (change,) = [c for c in sync.pending() if c.key == _uuid(conn, "person", scene.papa.id)]
    sync.acknowledge(change, 7)
    assert sync.server_version(SyncEntity.PERSON, change.key) == 7
    assert change not in sync.pending()


def test_une_modification_pendant_l_envoi_reste_a_envoyer(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    sync = SyncRepository(conn)
    cle = _uuid(conn, "person", scene.papa.id)
    (lue,) = [c for c in sync.pending() if c.key == cle]

    PersonRepository(conn).rename(scene.papa.id, "Papa Jean", "père")  # pendant l'envoi
    sync.acknowledge(lue, 1)

    (restante,) = [c for c in sync.pending() if c.key == cle]
    assert restante.revision > lue.revision


def test_un_ajout_acquitte_exige_une_version(conn: sqlite3.Connection, scene: Scene) -> None:
    sync = SyncRepository(conn)
    change = sync.pending()[0]
    with pytest.raises(ValueError):
        sync.acknowledge(change, None)
    assert change in sync.pending()


def test_une_suppression_acquittee_est_oubliee(conn: sqlite3.Connection, scene: Scene) -> None:
    _tout_envoyer(conn)
    sync = SyncRepository(conn)
    cle = _uuid(conn, "person", scene.papa.id)
    PersonRepository(conn).delete(scene.papa.id)
    (suppression,) = sync.pending()

    sync.acknowledge(suppression, None)

    assert sync.pending() == []
    assert sync.server_version(SyncEntity.PERSON, cle) is None


def test_les_changements_recus_ne_sont_pas_renvoyes(conn: sqlite3.Connection) -> None:
    sync = SyncRepository(conn)
    with sync.applying_remote():
        conn.execute(
            "INSERT INTO person (uuid, display_name, relationship, created_at) "
            "VALUES (?, 'Tata Nadine', 'tante', '2026-10-01T10:00:00+00:00')",
            (str(uuid.uuid4()),),
        )
    assert sync.pending() == []
    # Le journal reprend ensuite normalement.
    PersonRepository(conn).add("Tonton Alain", "oncle")
    assert len(sync.pending()) == 1


def test_une_erreur_annule_tous_les_changements_recus(conn: sqlite3.Connection) -> None:
    sync = SyncRepository(conn)
    with pytest.raises(RuntimeError), sync.applying_remote():
        conn.execute(
            "INSERT INTO person (uuid, display_name, relationship, created_at) "
            "VALUES (?, 'Tata Nadine', 'tante', '2026-10-01T10:00:00+00:00')",
            (str(uuid.uuid4()),),
        )
        raise RuntimeError("coupure réseau")
    assert PersonRepository(conn).list_all() == []
    assert conn.execute("SELECT applying_remote FROM sync_state").fetchone()[0] == 0


def test_le_numero_de_reception_ne_recule_pas(conn: sqlite3.Connection) -> None:
    sync = SyncRepository(conn)
    assert sync.last_pulled_seq() == 0
    sync.set_last_pulled_seq(42)
    assert sync.last_pulled_seq() == 42
    with pytest.raises(ValueError):
        sync.set_last_pulled_seq(41)


def test_le_consentement_n_a_pas_d_entree_propre(conn: sqlite3.Connection, scene: Scene) -> None:
    StoryRepository(conn).create(
        person_id=scene.papa.id,
        question_id=scene.q_jeux.id,
        duration_s=60.0,
        audio_path=Path("a.wav"),
        consent_statement=CONSENT,
    )
    entites = {c.entity for c in SyncRepository(conn).pending()}
    assert entites == {SyncEntity.PERSON, SyncEntity.THEME, SyncEntity.QUESTION, SyncEntity.STORY}


def test_pending_change_porte_sa_revision(conn: sqlite3.Connection, scene: Scene) -> None:
    revisions = [c.revision for c in SyncRepository(conn).pending()]
    assert revisions == sorted(revisions)
    assert len(set(revisions)) == len(revisions)
