import random
import sqlite3
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    PersonRepository,
    Repositories,
    StoryRepository,
    ThemeRepository,
)
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.graph import (
    FULL_MAX,
    STRONG_PER_STORY,
    Density,
    GraphFilter,
    GraphService,
    strongest_links,
)
from au_fil_d_une_vie.services.links import StoryLink


@pytest.fixture
def ids(conn: sqlite3.Connection) -> dict[str, int]:
    ids = list(load_demo(Repositories(conn)))
    return dict(zip(["ecole", "papi", "premier_jour", "plat", "travail", "etes"], ids, strict=True))


def _service(conn: sqlite3.Connection) -> GraphService:
    return GraphService(StoryRepository(conn), KeywordRepository(conn))


# Le fil et ses arcs (jeu de démo)


def test_les_recits_sont_ranges_dans_l_ordre_ou_ils_ont_ete_recueillis(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    vue = _service(conn).build()
    assert [s.id for s in vue.stories] == [
        ids["etes"],
        ids["travail"],
        ids["plat"],
        ids["premier_jour"],
        ids["papi"],
        ids["ecole"],
    ]
    positions = [s.position for s in vue.stories]
    assert positions[0] == 0.0 and positions[-1] == 1.0
    assert positions == sorted(positions)


def test_un_arc_relie_deux_recits_et_porte_leurs_mots(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    vue = _service(conn).build()
    arc = next(a for a in vue.arcs if {a.story_a, a.story_b} == {ids["ecole"], ids["papi"]})
    assert arc.story_a == ids["papi"]  # le plus ancien des deux d'abord
    assert arc.words == ("bourg",)
    ecole = next(
        a for a in vue.arcs if {a.story_a, a.story_b} == {ids["ecole"], ids["premier_jour"]}
    )
    assert set(ecole.words) == {"école", "institutrice", "craie"}
    assert len(vue.arcs) == 5
    assert [a.weight for a in vue.arcs] == sorted((a.weight for a in vue.arcs), reverse=True)


def test_le_recit_sans_lien_reste_sur_le_fil(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build()
    travail = vue.story(ids["travail"])
    assert travail is not None and not travail.linked
    assert not any(a.touches(ids["travail"]) for a in vue.arcs)


def test_les_mois_sont_reperes_sur_le_fil(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build()
    assert [m.month for m in vue.months] == [date(2026, 9, 1), date(2026, 10, 1)]
    octobre = vue.months[1]
    premier_d_octobre = vue.story(ids["premier_jour"])
    assert premier_d_octobre is not None and octobre.position == premier_d_octobre.position


def test_selection_par_defaut_et_groupes(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build()
    assert vue.busiest_story() == ids["ecole"]
    assert vue.groups == 1
    assert vue.density is Density.FULL
    assert vue.visible_arcs(set()) == vue.arcs  # palier complet : tous les arcs


def test_le_dessin_est_stable(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    premier, second = _service(conn).build(), _service(conn).build()
    assert premier == second


def test_un_recit_masque_disparait_du_graphe(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    StoryRepository(conn).set_hidden(ids["plat"], True)
    vue = _service(conn).build()
    assert vue.story(ids["plat"]) is None
    assert all("ferme" not in a.words for a in vue.arcs)


def test_graphe_vide(conn: sqlite3.Connection) -> None:
    vue = _service(conn).build()
    assert vue.stories == [] and vue.arcs == [] and vue.busiest_story() is None


def test_un_seul_recit_est_au_milieu_du_fil(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    stories = StoryRepository(conn)
    for story_id in list(ids.values())[1:]:
        stories.set_hidden(story_id, True)
    (seul,) = _service(conn).build().stories
    assert seul.position == 0.5


# Liens forts


def test_chaque_recit_garde_ses_liens_les_plus_forts() -> None:
    liens = [
        StoryLink(1, n, weight=10.0 - n, shared_keyword_ids=(n,)) for n in range(2, 8)
    ]  # le récit 1 a six liens, du plus fort (2) au plus faible (7)
    forts = strongest_links(liens, per_story=3)
    # Pour le récit 1, seuls ses 3 premiers comptent, mais chaque autre récit n'a qu'un
    # lien : il le garde. Aucun lien ne disparaît donc ici.
    assert forts == {(1, n) for n in range(2, 8)}
    liens += [StoryLink(n, n + 1, weight=20.0, shared_keyword_ids=(99,)) for n in (4, 5, 6)]
    forts = strongest_links(sorted(liens, key=lambda link: -link.weight), per_story=1)
    assert (1, 2) in forts  # le meilleur lien du récit 1
    assert (1, 6) not in forts  # ni le meilleur de 1, ni celui de 6 (qui préfère 5 ou 7)


# Grande famille (palier compact)


def _grande_famille(conn: sqlite3.Connection, count: int) -> list[int]:
    """Crée `count` récits fictifs avec des mots validés tirés d'un petit vocabulaire."""
    rng = random.Random(3)
    themes = ThemeRepository(conn)
    piste = themes.add_theme("vie", "Vie", 1)
    question = themes.add_question(piste.id, "Raconte-moi un souvenir.", 1)
    proches = [PersonRepository(conn).add(f"Proche {i}", "famille") for i in range(6)]
    stories, keywords = StoryRepository(conn), KeywordRepository(conn)
    vocabulaire = [f"mot{i}" for i in range(40)]
    debut = datetime(2026, 1, 3, 10, tzinfo=UTC)
    created = []
    for index in range(count):
        story = stories.create(
            person_id=proches[index % len(proches)].id,
            question_id=question.id,
            duration_s=120.0,
            audio_path=Path(f"grand/{index}.wav"),
            consent_statement="Consentement fictif.",
            recorded_at=debut + timedelta(days=index * 3),
        )
        for mot in rng.sample(vocabulaire, 4):
            keywords.add_validated(story.id, mot, mot)
        created.append(story.id)
    return created


def test_au_dela_du_palier_le_fil_devient_compact(conn: sqlite3.Connection) -> None:
    _grande_famille(conn, FULL_MAX + 1)
    assert _service(conn).build().density is Density.COMPACT


def test_en_compact_seuls_les_liens_forts_sont_traces_sauf_pour_le_focus(
    conn: sqlite3.Connection,
) -> None:
    recits = _grande_famille(conn, 80)
    vue = _service(conn).build()
    assert len(vue.stories) == 80  # aucun récit n'est retiré du fil
    sans_focus = vue.visible_arcs(set())
    assert all(a.strong for a in sans_focus)
    assert len(sans_focus) < len(vue.arcs)
    # Chaque récit relié garde au moins un arc visible, au plus ses liens forts... ou ceux
    # que les autres récits ont choisis.
    for story_id in recits:
        if any(a.touches(story_id) for a in vue.arcs):
            assert any(a.touches(story_id) for a in sans_focus)
    # Le récit en focus montre tous ses liens.
    focus = recits[10]
    tous = [a for a in vue.arcs if a.touches(focus)]
    assert len(tous) > STRONG_PER_STORY
    visibles = vue.visible_arcs({focus})
    assert all(a in visibles for a in tous)


def test_le_graphe_d_une_grande_famille_se_calcule_vite(conn: sqlite3.Connection) -> None:
    _grande_famille(conn, 200)
    debut = time.perf_counter()
    vue = _service(conn).build()
    assert len(vue.stories) == 200
    assert time.perf_counter() - debut < 2.0


# Filtres


def _personne(conn: sqlite3.Connection, nom: str) -> int:
    return next(p.id for p in PersonRepository(conn).list_all() if p.display_name == nom)


def test_filtrer_sur_un_proche(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build(GraphFilter(person_id=_personne(conn, "Papa")))
    assert {s.id for s in vue.stories} == {ids["premier_jour"], ids["plat"]}
    assert vue.total == 6
    assert [s.position for s in vue.stories] == [0.0, 1.0]  # le fil est réparti à nouveau
    # Les deux récits de Papa ne partagent aucun mot : aucun arc entre eux.
    assert vue.arcs == []


def test_filtrer_sur_un_mot(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    service = _service(conn)
    bourg = next(o for o in service.filter_options().words if o.label == "bourg")
    vue = service.build(GraphFilter(keyword_id=bourg.id))
    assert {s.id for s in vue.stories} == {ids["ecole"], ids["papi"], ids["etes"]}
    assert all("bourg" in a.words for a in vue.arcs if {a.story_a, a.story_b} <= {ids["ecole"]})
    assert vue.keyword_ids["bourg"] == bourg.id


def test_la_force_d_un_lien_ne_change_pas_quand_on_filtre(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    service = _service(conn)
    tout = service.build()
    enfance = next(o for o in service.filter_options().themes if o.label == "Enfance")
    filtre = service.build(GraphFilter(theme_id=enfance.id))
    assert filtre.arcs
    for arc in filtre.arcs:
        meme = next(a for a in tout.arcs if (a.story_a, a.story_b) == (arc.story_a, arc.story_b))
        assert arc.weight == meme.weight and arc.words == meme.words


def test_les_filtres_se_combinent(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    service = _service(conn)
    bourg = next(o for o in service.filter_options().words if o.label == "bourg")
    yvonne = _personne(conn, "Mamie Yvonne")
    vue = service.build(GraphFilter(person_id=yvonne, keyword_id=bourg.id))
    assert {s.id for s in vue.stories} == {ids["ecole"], ids["papi"], ids["etes"]}
    papa = _personne(conn, "Papa")
    assert service.build(GraphFilter(person_id=papa, keyword_id=bourg.id)).stories == []


def test_les_choix_de_filtre_ne_proposent_que_ce_qui_a_des_recits(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    options = _service(conn).filter_options()
    assert {o.label for o in options.people} == {"Mamie Yvonne", "Papa", "Tonton Alain"}
    assert "Tata Nadine" not in {o.label for o in options.people}  # aucun récit
    assert {o.label for o in options.words} == {
        "bourg",
        "sabots",
        "ferme",
        "école",
        "institutrice",
        "craie",
    }
    assert options.words[0].label == "bourg"  # le plus présent d'abord (3 récits)
    assert GraphFilter().active is False
    assert GraphFilter(theme_id=1).active is True
