-- Schéma initial d'Au fil d'une vie.
-- Dates : texte ISO 8601 en UTC. Booléens : INTEGER 0 ou 1.
-- Toutes les données liées à un récit sont supprimées en cascade avec lui (droit à l'effacement).

-- Le jeune qui mène la quête (une seule ligne : l'application est mono-utilisateur).
CREATE TABLE profile (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    first_name          TEXT    NOT NULL CHECK (length(trim(first_name)) > 0),
    under_15            INTEGER NOT NULL CHECK (under_15 IN (0, 1)),
    parental_consent_at TEXT,
    created_at          TEXT    NOT NULL,
    -- Sous 15 ans, l'accord d'un parent est obligatoire.
    CHECK (under_15 = 0 OR parental_consent_at IS NOT NULL)
);

-- Proche interrogé.
CREATE TABLE person (
    id           INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
    relationship TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

-- Piste (thème) et ses questions.
CREATE TABLE theme (
    id       INTEGER PRIMARY KEY,
    slug     TEXT    NOT NULL UNIQUE,
    label    TEXT    NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE question (
    id       INTEGER PRIMARY KEY,
    theme_id INTEGER NOT NULL REFERENCES theme (id) ON DELETE CASCADE,
    text     TEXT    NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    UNIQUE (theme_id, text)
);

-- Récit : un enregistrement.
CREATE TABLE story (
    id          INTEGER PRIMARY KEY,
    person_id   INTEGER NOT NULL REFERENCES person (id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES question (id) ON DELETE RESTRICT,
    recorded_at TEXT    NOT NULL,
    duration_s  REAL    NOT NULL CHECK (duration_s >= 0),
    audio_path  TEXT    NOT NULL,  -- relatif au dossier audio, pour rester portable
    is_hidden   INTEGER NOT NULL DEFAULT 0 CHECK (is_hidden IN (0, 1)),
    status      TEXT    NOT NULL DEFAULT 'recorded'
                CHECK (status IN ('recorded', 'transcribing', 'transcribed'))
);

CREATE INDEX idx_story_person ON story (person_id);
CREATE INDEX idx_story_question ON story (question_id);

-- Consentement du proche, un par enregistrement.
CREATE TABLE consent (
    id        INTEGER PRIMARY KEY,
    story_id  INTEGER NOT NULL UNIQUE REFERENCES story (id) ON DELETE CASCADE,
    given_at  TEXT    NOT NULL,
    statement TEXT    NOT NULL  -- texte exact accepté, pour la trace
);

-- Texte brut issu de la transcription et version livre corrigée.
CREATE TABLE transcript (
    story_id   INTEGER PRIMARY KEY REFERENCES story (id) ON DELETE CASCADE,
    raw_text   TEXT NOT NULL,
    book_text  TEXT,
    language   TEXT NOT NULL DEFAULT 'fr',
    updated_at TEXT NOT NULL
);

-- Mots-clés (lemme unique) et leur lien avec les récits.
CREATE TABLE keyword (
    id    INTEGER PRIMARY KEY,
    lemma TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL
);

CREATE TABLE story_keyword (
    story_id     INTEGER NOT NULL REFERENCES story (id) ON DELETE CASCADE,
    keyword_id   INTEGER NOT NULL REFERENCES keyword (id) ON DELETE CASCADE,
    weight       REAL    NOT NULL DEFAULT 0 CHECK (weight >= 0),
    -- 0 : proposé par l'analyse, 1 : validé par l'utilisateur.
    is_validated INTEGER NOT NULL DEFAULT 0 CHECK (is_validated IN (0, 1)),
    PRIMARY KEY (story_id, keyword_id)
);

CREATE INDEX idx_story_keyword_keyword ON story_keyword (keyword_id);

-- Un mot-clé qui n'est plus rattaché à aucun récit disparaît.
CREATE TRIGGER trg_keyword_orphan
AFTER DELETE ON story_keyword
WHEN NOT EXISTS (SELECT 1 FROM story_keyword WHERE keyword_id = OLD.keyword_id)
BEGIN
    DELETE FROM keyword WHERE id = OLD.keyword_id;
END;

-- « Mon carnet » : ce que l'utilisateur retient d'un récit.
CREATE TABLE note (
    story_id   INTEGER PRIMARY KEY REFERENCES story (id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
