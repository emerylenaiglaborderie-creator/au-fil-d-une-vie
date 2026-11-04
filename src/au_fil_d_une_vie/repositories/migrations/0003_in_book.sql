-- Choix des récits qui entrent dans le livre de famille (ajout volontaire).
ALTER TABLE story ADD COLUMN in_book INTEGER NOT NULL DEFAULT 0 CHECK (in_book IN (0, 1));
