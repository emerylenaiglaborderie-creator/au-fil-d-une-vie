-- Préparation de la synchronisation avec le serveur familial (brief, section 7.3).
--
-- Principes :
-- * Les identifiants entiers restent locaux à chaque poste. Les données échangées avec
--   le serveur sont désignées par un UUID, attribué à la création, ou par l'UUID du
--   récit pour ce qui en dépend (texte, note, mots-clés validés).
-- * Les suppressions restent de vraies suppressions (droit à l'effacement) : le journal
--   ne garde que l'identifiant de ce qui a été supprimé, jamais son contenu.
-- * Des triggers tiennent le journal des modifications locales à envoyer (sync_outbox).
--   Ils se taisent pendant l'application des changements reçus du serveur
--   (sync_state.applying_remote = 1), pour ne pas les renvoyer.
-- * Données non synchronisées : profil (propre à chaque poste), statut de transcription
--   (traitement local), mots-clés proposés mais non validés, poids, liens.
-- * Le consentement est immuable et créé avec le récit : il voyage avec lui.

-- 1. Identifiants universels

ALTER TABLE person ADD COLUMN uuid TEXT;
ALTER TABLE theme ADD COLUMN uuid TEXT;
ALTER TABLE question ADD COLUMN uuid TEXT;
ALTER TABLE follow_up ADD COLUMN uuid TEXT;
ALTER TABLE story ADD COLUMN uuid TEXT;

-- UUID version 4 pour les lignes existantes, calculé en SQL.
UPDATE person SET uuid = lower(
    hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2)
    || '-' || substr('89ab', 1 + abs(random()) % 4, 1) || substr(hex(randomblob(2)), 2)
    || '-' || hex(randomblob(6)));
UPDATE theme SET uuid = lower(
    hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2)
    || '-' || substr('89ab', 1 + abs(random()) % 4, 1) || substr(hex(randomblob(2)), 2)
    || '-' || hex(randomblob(6)));
UPDATE question SET uuid = lower(
    hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2)
    || '-' || substr('89ab', 1 + abs(random()) % 4, 1) || substr(hex(randomblob(2)), 2)
    || '-' || hex(randomblob(6)));
UPDATE follow_up SET uuid = lower(
    hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2)
    || '-' || substr('89ab', 1 + abs(random()) % 4, 1) || substr(hex(randomblob(2)), 2)
    || '-' || hex(randomblob(6)));
UPDATE story SET uuid = lower(
    hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2)
    || '-' || substr('89ab', 1 + abs(random()) % 4, 1) || substr(hex(randomblob(2)), 2)
    || '-' || hex(randomblob(6)));

CREATE UNIQUE INDEX idx_person_uuid ON person (uuid);
CREATE UNIQUE INDEX idx_theme_uuid ON theme (uuid);
CREATE UNIQUE INDEX idx_question_uuid ON question (uuid);
CREATE UNIQUE INDEX idx_follow_up_uuid ON follow_up (uuid);
CREATE UNIQUE INDEX idx_story_uuid ON story (uuid);

-- SQLite ne permet pas d'ajouter une colonne NOT NULL sans valeur par défaut constante :
-- l'obligation et l'immuabilité de l'UUID sont garanties par des triggers.
CREATE TRIGGER trg_person_uuid_required BEFORE INSERT ON person WHEN NEW.uuid IS NULL
BEGIN SELECT RAISE(ABORT, 'uuid obligatoire'); END;
CREATE TRIGGER trg_theme_uuid_required BEFORE INSERT ON theme WHEN NEW.uuid IS NULL
BEGIN SELECT RAISE(ABORT, 'uuid obligatoire'); END;
CREATE TRIGGER trg_question_uuid_required BEFORE INSERT ON question WHEN NEW.uuid IS NULL
BEGIN SELECT RAISE(ABORT, 'uuid obligatoire'); END;
CREATE TRIGGER trg_follow_up_uuid_required BEFORE INSERT ON follow_up WHEN NEW.uuid IS NULL
BEGIN SELECT RAISE(ABORT, 'uuid obligatoire'); END;
CREATE TRIGGER trg_story_uuid_required BEFORE INSERT ON story WHEN NEW.uuid IS NULL
BEGIN SELECT RAISE(ABORT, 'uuid obligatoire'); END;

CREATE TRIGGER trg_person_uuid_fixed BEFORE UPDATE OF uuid ON person
WHEN NEW.uuid IS NOT OLD.uuid
BEGIN SELECT RAISE(ABORT, 'uuid non modifiable'); END;
CREATE TRIGGER trg_theme_uuid_fixed BEFORE UPDATE OF uuid ON theme
WHEN NEW.uuid IS NOT OLD.uuid
BEGIN SELECT RAISE(ABORT, 'uuid non modifiable'); END;
CREATE TRIGGER trg_question_uuid_fixed BEFORE UPDATE OF uuid ON question
WHEN NEW.uuid IS NOT OLD.uuid
BEGIN SELECT RAISE(ABORT, 'uuid non modifiable'); END;
CREATE TRIGGER trg_follow_up_uuid_fixed BEFORE UPDATE OF uuid ON follow_up
WHEN NEW.uuid IS NOT OLD.uuid
BEGIN SELECT RAISE(ABORT, 'uuid non modifiable'); END;
CREATE TRIGGER trg_story_uuid_fixed BEFORE UPDATE OF uuid ON story
WHEN NEW.uuid IS NOT OLD.uuid
BEGIN SELECT RAISE(ABORT, 'uuid non modifiable'); END;

-- 2. État de la synchronisation

-- Une seule ligne : avancement de la réception et interrupteur du journal.
CREATE TABLE sync_state (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    -- Numéro de la dernière modification du serveur déjà reçue.
    last_pulled_seq  INTEGER NOT NULL DEFAULT 0 CHECK (last_pulled_seq >= 0),
    -- 1 pendant l'application des changements reçus : le journal ne les enregistre pas.
    applying_remote  INTEGER NOT NULL DEFAULT 0 CHECK (applying_remote IN (0, 1))
);

INSERT INTO sync_state (id) VALUES (1);

-- Données que le serveur connaît déjà, avec la version qu'il leur a donnée.
-- Une modification envoyée s'appuie sur cette version (verrouillage optimiste).
CREATE TABLE sync_known (
    entity         TEXT    NOT NULL,
    entity_key     TEXT    NOT NULL,
    server_version INTEGER NOT NULL CHECK (server_version > 0),
    PRIMARY KEY (entity, entity_key)
);

-- Journal des modifications locales à envoyer : une ligne par donnée, la dernière
-- opération l'emporte. Les triggers remplacent une ligne par DELETE puis INSERT
-- explicites : dans un trigger, INSERT OR REPLACE hériterait de la règle de conflit
-- de l'instruction déclenchante (ON CONFLICT DO UPDATE par exemple) et échouerait. Une donnée créée puis supprimée avant tout envoi disparaît
-- du journal sans rien laisser.
-- Chaque écriture remplace la ligne et lui donne un nouveau numéro (AUTOINCREMENT :
-- jamais réutilisé). L'acquittement vise ce numéro : une donnée modifiée pendant
-- un envoi reste dans le journal.
CREATE TABLE sync_outbox (
    revision   INTEGER PRIMARY KEY AUTOINCREMENT,
    entity     TEXT    NOT NULL CHECK (entity IN (
                   'person', 'theme', 'question', 'follow_up', 'story',
                   'transcript', 'note', 'story_keywords')),
    entity_key TEXT    NOT NULL,  -- UUID de la donnée, ou du récit pour ce qui en dépend
    operation  TEXT    NOT NULL CHECK (operation IN ('upsert', 'delete')),
    changed_at TEXT    NOT NULL,
    UNIQUE (entity, entity_key)
);

-- 3. Journal : données désignées par leur propre UUID

-- Proches
CREATE TRIGGER trg_person_sync_insert AFTER INSERT ON person
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'person' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('person', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_person_sync_update AFTER UPDATE OF display_name, relationship ON person
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'person' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('person', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_person_sync_delete AFTER DELETE ON person
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'person' AND entity_key = OLD.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'person', OLD.uuid, 'delete', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    WHERE EXISTS (SELECT 1 FROM sync_known WHERE entity = 'person' AND entity_key = OLD.uuid);
END;

-- Pistes
CREATE TRIGGER trg_theme_sync_insert AFTER INSERT ON theme
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'theme' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('theme', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_theme_sync_update AFTER UPDATE OF slug, label, position ON theme
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'theme' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('theme', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_theme_sync_delete AFTER DELETE ON theme
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'theme' AND entity_key = OLD.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'theme', OLD.uuid, 'delete', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    WHERE EXISTS (SELECT 1 FROM sync_known WHERE entity = 'theme' AND entity_key = OLD.uuid);
END;

-- Questions
CREATE TRIGGER trg_question_sync_insert AFTER INSERT ON question
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'question' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('question', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_question_sync_update AFTER UPDATE OF theme_id, text, position ON question
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'question' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('question', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_question_sync_delete AFTER DELETE ON question
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'question' AND entity_key = OLD.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'question', OLD.uuid, 'delete', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    WHERE EXISTS (SELECT 1 FROM sync_known WHERE entity = 'question' AND entity_key = OLD.uuid);
END;

-- Relances
CREATE TRIGGER trg_follow_up_sync_insert AFTER INSERT ON follow_up
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'follow_up' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('follow_up', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_follow_up_sync_update AFTER UPDATE OF question_id, text, position ON follow_up
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'follow_up' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('follow_up', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_follow_up_sync_delete AFTER DELETE ON follow_up
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'follow_up' AND entity_key = OLD.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'follow_up', OLD.uuid, 'delete', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    WHERE EXISTS (SELECT 1 FROM sync_known WHERE entity = 'follow_up' AND entity_key = OLD.uuid);
END;

-- Récits (le statut de transcription est local : il n'est pas journalisé)
CREATE TRIGGER trg_story_sync_insert AFTER INSERT ON story
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'story' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('story', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

CREATE TRIGGER trg_story_sync_update
AFTER UPDATE OF person_id, question_id, recorded_at, duration_s, audio_path, is_hidden, in_book
ON story
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox WHERE entity = 'story' AND entity_key = NEW.uuid;
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    VALUES ('story', NEW.uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'));
END;

-- La suppression d'un récit couvre son texte, sa note et ses mots-clés : leurs propres
-- entrées du journal deviennent inutiles.
CREATE TRIGGER trg_story_sync_delete AFTER DELETE ON story
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox
    WHERE entity_key = OLD.uuid AND entity IN ('story', 'transcript', 'note', 'story_keywords');
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'story', OLD.uuid, 'delete', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    WHERE EXISTS (SELECT 1 FROM sync_known WHERE entity = 'story' AND entity_key = OLD.uuid);
END;

-- 4. Journal : données désignées par l'UUID de leur récit
-- Quand le récit lui-même est supprimé, ses dépendances ne sont pas journalisées
-- (la condition EXISTS sur story l'exclut) : la suppression du récit suffit.

-- Texte du récit
CREATE TRIGGER trg_transcript_sync_insert AFTER INSERT ON transcript
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'transcript' AND entity_key = (SELECT uuid FROM story WHERE id = NEW.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'transcript', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = NEW.story_id;
END;

CREATE TRIGGER trg_transcript_sync_update AFTER UPDATE OF raw_text, book_text, language
ON transcript
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'transcript' AND entity_key = (SELECT uuid FROM story WHERE id = NEW.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'transcript', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = NEW.story_id;
END;

-- « Mon carnet » (une note vidée est supprimée)
CREATE TRIGGER trg_note_sync_insert AFTER INSERT ON note
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'note' AND entity_key = (SELECT uuid FROM story WHERE id = NEW.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'note', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = NEW.story_id;
END;

CREATE TRIGGER trg_note_sync_update AFTER UPDATE OF content ON note
WHEN (SELECT applying_remote FROM sync_state) = 0
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'note' AND entity_key = (SELECT uuid FROM story WHERE id = NEW.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'note', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = NEW.story_id;
END;

CREATE TRIGGER trg_note_sync_delete AFTER DELETE ON note
WHEN (SELECT applying_remote FROM sync_state) = 0
     AND EXISTS (SELECT 1 FROM story WHERE id = OLD.story_id)
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'note' AND entity_key = (SELECT uuid FROM story WHERE id = OLD.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'note', s.uuid, 'delete', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story AS s
    WHERE s.id = OLD.story_id
      AND EXISTS (SELECT 1 FROM sync_known WHERE entity = 'note' AND entity_key = s.uuid);
END;

-- Mots-clés validés d'un récit, échangés comme un ensemble (fusion en cas de conflit).
-- Les propositions non validées restent locales.
CREATE TRIGGER trg_story_keyword_sync_insert AFTER INSERT ON story_keyword
WHEN (SELECT applying_remote FROM sync_state) = 0 AND NEW.is_validated = 1
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'story_keywords' AND entity_key = (SELECT uuid FROM story WHERE id = NEW.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'story_keywords', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = NEW.story_id;
END;

CREATE TRIGGER trg_story_keyword_sync_update AFTER UPDATE OF is_validated ON story_keyword
WHEN (SELECT applying_remote FROM sync_state) = 0 AND NEW.is_validated <> OLD.is_validated
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'story_keywords' AND entity_key = (SELECT uuid FROM story WHERE id = NEW.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'story_keywords', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = NEW.story_id;
END;

CREATE TRIGGER trg_story_keyword_sync_delete AFTER DELETE ON story_keyword
WHEN (SELECT applying_remote FROM sync_state) = 0 AND OLD.is_validated = 1
     AND EXISTS (SELECT 1 FROM story WHERE id = OLD.story_id)
BEGIN
    DELETE FROM sync_outbox
    WHERE entity = 'story_keywords' AND entity_key = (SELECT uuid FROM story WHERE id = OLD.story_id);
    INSERT INTO sync_outbox (entity, entity_key, operation, changed_at)
    SELECT 'story_keywords', uuid, 'upsert', strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
    FROM story WHERE id = OLD.story_id;
END;
