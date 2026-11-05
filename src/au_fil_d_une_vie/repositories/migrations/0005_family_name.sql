-- Nom de famille, facultatif, affiché sur l'arbre d'accueil (« Famille Morvan »).
-- Le profil reste propre à chaque poste : ce nom n'est pas synchronisé.
ALTER TABLE profile ADD COLUMN family_name TEXT
    CHECK (family_name IS NULL OR length(trim(family_name)) > 0);
