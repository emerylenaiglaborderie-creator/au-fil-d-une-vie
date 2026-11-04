import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.repositories import (
    KeywordCandidate,
    KeywordRepository,
    NoteRepository,
    PersonRepository,
    ProfileRepository,
    StoryRepository,
    ThemeRepository,
    TranscriptRepository,
)
from tests.conftest import CONSENT, Scene


def _compte(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


# Profil et consentement parental


def test_profil_de_plus_de_15_ans(conn: sqlite3.Connection) -> None:
    profil = ProfileRepository(conn).save("Camille", under_15=False)
    assert profil.first_name == "Camille"
    assert profil.parental_consent_at is None


def test_sous_15_ans_l_accord_parental_est_obligatoire(conn: sqlite3.Connection) -> None:
    repo = ProfileRepository(conn)
    with pytest.raises(sqlite3.IntegrityError):
        repo.save("Camille", under_15=True)
    profil = repo.save("Camille", under_15=True, parental_consent_at=datetime.now(UTC))
    assert profil.parental_consent_at is not None


def test_le_profil_est_unique(conn: sqlite3.Connection) -> None:
    repo = ProfileRepository(conn)
    repo.save("Camille", under_15=False)
    repo.save("Léo", under_15=False)
    assert _compte(conn, "profile") == 1
    profil = repo.get()
    assert profil is not None and profil.first_name == "Léo"


# Récits et consentement du proche


def test_un_recit_est_cree_avec_son_consentement(conn: sqlite3.Connection, scene: Scene) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    consentement = StoryRepository(conn).consent_for(recit.id)
    assert consentement is not None
    assert consentement.statement == CONSENT
    assert recit.status is StoryStatus.RECORDED
    assert recit.audio_path == Path("2026/recit.wav")


def test_pas_de_recit_sans_consentement(conn: sqlite3.Connection, scene: Scene) -> None:
    with pytest.raises(ValueError):
        StoryRepository(conn).create(
            scene.yvonne.id, scene.q_ecole.id, 10.0, Path("a.wav"), consent_statement="  "
        )
    assert _compte(conn, "story") == 0


def test_les_recits_sont_tries_du_plus_recent(conn: sqlite3.Connection, scene: Scene) -> None:
    repo = StoryRepository(conn)
    ancien = repo.create(
        scene.yvonne.id,
        scene.q_ecole.id,
        1.0,
        Path("a.wav"),
        CONSENT,
        recorded_at=datetime(2026, 9, 20, tzinfo=UTC),
    )
    recent = repo.create(
        scene.papa.id,
        scene.q_jeux.id,
        1.0,
        Path("b.wav"),
        CONSENT,
        recorded_at=datetime(2026, 10, 12, tzinfo=UTC),
    )
    assert [s.id for s in repo.list_all()] == [recent.id, ancien.id]


def test_un_recit_masque_disparait_des_listes(conn: sqlite3.Connection, scene: Scene) -> None:
    repo = StoryRepository(conn)
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    repo.set_hidden(recit.id, True)
    assert repo.list_all() == []
    assert len(repo.list_all(include_hidden=True)) == 1
    assert ThemeRepository(conn).progress()[scene.q_ecole.theme_id] == (0, 2)


def test_supprimer_un_recit_efface_tout_ce_qui_s_y_rattache(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    TranscriptRepository(conn).save_raw(recit.id, "J'allais à l'école en sabots.")
    KeywordRepository(conn).propose(recit.id, [KeywordCandidate("sabot", "sabots", 0.8)])
    NoteRepository(conn).save(recit.id, "Elle marchait trois kilomètres.")

    StoryRepository(conn).delete(recit.id)

    for table in ("story", "consent", "transcript", "story_keyword", "keyword", "note"):
        assert _compte(conn, table) == 0, table


def test_supprimer_un_proche_supprime_ses_recits(conn: sqlite3.Connection, scene: Scene) -> None:
    scene.story(conn, scene.yvonne, scene.q_ecole)
    scene.story(conn, scene.papa, scene.q_jeux)
    PersonRepository(conn).delete(scene.yvonne.id)
    restants = StoryRepository(conn).list_all(include_hidden=True)
    assert [s.person_id for s in restants] == [scene.papa.id]


def test_changer_le_statut(conn: sqlite3.Connection, scene: Scene) -> None:
    repo = StoryRepository(conn)
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    repo.set_status(recit.id, StoryStatus.TRANSCRIBED)
    relu = repo.get(recit.id)
    assert relu is not None and relu.status is StoryStatus.TRANSCRIBED


# Proches et pistes


def test_nombre_de_recits_par_proche(conn: sqlite3.Connection, scene: Scene) -> None:
    PersonRepository(conn).add("Tata Nadine", "tante")
    scene.story(conn, scene.yvonne, scene.q_ecole)
    scene.story(conn, scene.yvonne, scene.q_jeux)
    scene.story(conn, scene.papa, scene.q_ecole)
    comptes = [(p.display_name, n) for p, n in PersonRepository(conn).list_with_story_count()]
    assert comptes == [("Mamie Yvonne", 2), ("Papa", 1), ("Tata Nadine", 0)]


def test_progression_par_piste(conn: sqlite3.Connection, scene: Scene) -> None:
    themes = ThemeRepository(conn)
    musique = themes.add_theme("musique", "Musique", 5)
    scene.story(conn, scene.yvonne, scene.q_ecole)
    scene.story(conn, scene.papa, scene.q_ecole)
    progression = themes.progress()
    assert progression[scene.q_ecole.theme_id] == (1, 2)
    assert progression[musique.id] == (0, 0)


def test_une_question_avec_des_recits_ne_peut_pas_etre_supprimee(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    scene.story(conn, scene.yvonne, scene.q_ecole)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM question WHERE id = ?", (scene.q_ecole.id,))


# Textes


def test_la_version_livre_survit_a_une_nouvelle_transcription(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    repo = TranscriptRepository(conn)
    repo.save_raw(recit.id, "l'ecole du bour")
    repo.save_book_text(recit.id, "L'école du bourg.")
    repo.save_raw(recit.id, "l'école du bour")
    texte = repo.get(recit.id)
    assert texte is not None
    assert texte.raw_text == "l'école du bour"
    assert texte.display_text == "L'école du bourg."


def test_pas_de_version_livre_sans_texte_brut(conn: sqlite3.Connection, scene: Scene) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    with pytest.raises(LookupError):
        TranscriptRepository(conn).save_book_text(recit.id, "Texte")


# Mots-clés


def test_proposer_puis_valider_des_mots_cles(conn: sqlite3.Connection, scene: Scene) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    repo = KeywordRepository(conn)
    repo.propose(
        recit.id, [KeywordCandidate("école", "école", 0.9), KeywordCandidate("craie", "craie", 0.4)]
    )
    mots = repo.for_story(recit.id)
    assert [m.keyword.lemma for m in mots] == ["école", "craie"]
    assert repo.for_story(recit.id, validated_only=True) == []

    repo.set_validated(recit.id, mots[0].keyword.id, True)
    # Une nouvelle analyse met le poids à jour sans perdre la validation.
    repo.propose(recit.id, [KeywordCandidate("école", "école", 0.7)])
    valides = repo.for_story(recit.id, validated_only=True)
    assert [(m.keyword.lemma, m.weight) for m in valides] == [("école", 0.7)]


def test_un_mot_partage_est_stocke_une_seule_fois(conn: sqlite3.Connection, scene: Scene) -> None:
    r1 = scene.story(conn, scene.yvonne, scene.q_ecole)
    r2 = scene.story(conn, scene.papa, scene.q_ecole)
    repo = KeywordRepository(conn)
    repo.propose(r1.id, [KeywordCandidate("école", "école", 0.9)])
    repo.propose(r2.id, [KeywordCandidate("école", "École", 0.5)])
    assert _compte(conn, "keyword") == 1

    repo.remove(r1.id, repo.for_story(r1.id)[0].keyword.id)
    assert _compte(conn, "keyword") == 1  # encore utilisé par r2


def test_les_couples_valides_excluent_les_recits_masques(
    conn: sqlite3.Connection, scene: Scene
) -> None:
    r1 = scene.story(conn, scene.yvonne, scene.q_ecole)
    r2 = scene.story(conn, scene.papa, scene.q_ecole)
    repo = KeywordRepository(conn)
    for recit in (r1, r2):
        repo.propose(recit.id, [KeywordCandidate("école", "école", 0.9)])
        repo.set_validated(recit.id, repo.for_story(recit.id)[0].keyword.id, True)
    assert len(repo.validated_pairs()) == 2

    StoryRepository(conn).set_hidden(r2.id, True)
    assert [story_id for story_id, _ in repo.validated_pairs()] == [r1.id]


# Carnet


def test_carnet(conn: sqlite3.Connection, scene: Scene) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    repo = NoteRepository(conn)
    repo.save(recit.id, "Première version")
    repo.save(recit.id, "Ce que j'en retiens")
    note = repo.get(recit.id)
    assert note is not None and note.content == "Ce que j'en retiens"
    repo.save(recit.id, "   ")
    assert repo.get(recit.id) is None


def test_un_nouveau_recit_n_est_pas_dans_le_livre(conn: sqlite3.Connection, scene: Scene) -> None:
    repo = StoryRepository(conn)
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    assert not recit.in_book
    repo.set_in_book(recit.id, True)
    relu = repo.get(recit.id)
    assert relu is not None and relu.in_book
