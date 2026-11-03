-- Relances « Pour creuser » proposées pendant l'interview, par question.
CREATE TABLE follow_up (
    id          INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES question (id) ON DELETE CASCADE,
    text        TEXT    NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    UNIQUE (question_id, text)
);

CREATE INDEX idx_follow_up_question ON follow_up (question_id);
