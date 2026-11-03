"""Point d'entrée de l'application."""

from au_fil_d_une_vie import __version__
from au_fil_d_une_vie.config import data_dir


def main() -> None:
    """Lance l'application (l'interface viendra une fois le toolkit choisi)."""
    print(f"Au fil d'une vie {__version__}")
    print(f"Données locales : {data_dir()}")


if __name__ == "__main__":
    main()
