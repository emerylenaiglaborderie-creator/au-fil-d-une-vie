"""Point d'entrée de l'application."""

import argparse

from au_fil_d_une_vie import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="au-fil-d-une-vie", description="Partir en quête de son histoire familiale."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="ouvrir une base temporaire remplie avec le jeu de démo fictif",
    )
    parser.add_argument(
        "--modele",
        choices=("small", "base"),
        default="small",
        help="modèle de transcription : small (meilleur) ou base (plus rapide, machine modeste)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    # Imports tardifs : --help et --version restent instantanés.
    from au_fil_d_une_vie.bootstrap import open_services
    from au_fil_d_une_vie.ui.app import run

    raise SystemExit(run(open_services(demo=args.demo, model_size=args.modele)))


if __name__ == "__main__":
    main()
