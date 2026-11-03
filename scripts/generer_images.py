"""Génère les images de l'interface à partir du logo source.

    uv run python scripts/generer_images.py

- arbre.png : l'arbre seul (sans le texte), fond blanc rendu transparent ;
- logo.png : le logo complet réduit, fond blanc rendu transparent ;
- lavis.png : le lavis aquarelle décoratif (remplace le filtre SVG de la maquette).

Rendre le blanc transparent (« dé-multiplier ») donne, sur n'importe quel fond clair,
le même résultat que le mode de fusion multiply de la maquette.
"""

import math
import random
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "assets" / "logo" / "logo-complet.png"
SORTIE = RACINE / "src" / "au_fil_d_une_vie" / "ui" / "resources" / "images"

ZONE_ARBRE = QRect(380, 190, 1260, 1360)  # en pixels du logo source (2000 x 2000)
ZONE_LOGO = QRect(380, 190, 1260, 1620)


def blanc_vers_transparent(image: QImage) -> QImage:
    """Convertit le fond blanc en transparence, couleurs corrigées en conséquence."""
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            r, g, b = c.red(), c.green(), c.blue()
            alpha = 255 - min(r, g, b)
            if alpha == 0:
                image.setPixelColor(x, y, QColor(0, 0, 0, 0))
                continue
            a = alpha / 255

            def canal(v: int, a: float = a) -> int:
                return max(0, min(255, round((v - (1 - a) * 255) / a)))

            image.setPixelColor(x, y, QColor(canal(r), canal(g), canal(b), alpha))
    return image


def reduire(image: QImage, largeur: int) -> QImage:
    return image.scaledToWidth(largeur, Qt.TransformationMode.SmoothTransformation)


def tache(cx: float, cy: float, rx: float, ry: float, rng: random.Random) -> QPainterPath:
    """Ellipse aux bords irréguliers, façon goutte d'aquarelle."""
    harmoniques = [(k, rng.uniform(0.02, 0.09), rng.uniform(0, math.tau)) for k in (2, 3, 5, 7)]
    chemin = QPainterPath()
    for i in range(181):
        t = math.tau * i / 180
        f = 1 + sum(amp * math.sin(k * t + phase) for k, amp, phase in harmoniques)
        point = QPointF(cx + rx * f * math.cos(t), cy + ry * f * math.sin(t))
        if i == 0:
            chemin.moveTo(point)
        else:
            chemin.lineTo(point)
    return chemin


def flouter(image: QImage, facteur: int) -> QImage:
    """Flou doux par réduction puis agrandissement lissés."""
    petite = image.scaled(
        image.width() // facteur,
        image.height() // facteur,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return petite.scaled(
        image.size(),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def lavis() -> QImage:
    """Trois masses vertes superposées en couches transparentes (graine fixe)."""
    rng = random.Random(7)
    image = QImage(760, 620, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    peintre.setPen(Qt.PenStyle.NoPen)
    masses = [
        (470, 210, 210, 150, "#A9CB6E"),
        (350, 330, 170, 120, "#CFE0A0"),
        (560, 360, 140, 100, "#7FB04D"),
    ]
    for cx, cy, rx, ry, teinte in masses:
        for _ in range(14):
            couleur = QColor(teinte)
            couleur.setAlpha(rng.randint(26, 46))
            peintre.setBrush(couleur)
            echelle = rng.uniform(0.7, 1.05)
            peintre.drawPath(
                tache(
                    cx + rng.uniform(-25, 25),
                    cy + rng.uniform(-20, 20),
                    rx * echelle,
                    ry * echelle,
                    rng,
                )
            )
    peintre.end()
    return flouter(image, 3)


def main() -> None:
    _app = QGuiApplication(sys.argv)
    SORTIE.mkdir(parents=True, exist_ok=True)
    source = QImage(str(SOURCE))
    if source.isNull():
        raise SystemExit(f"Logo introuvable : {SOURCE}")

    blanc_vers_transparent(reduire(source.copy(ZONE_ARBRE), 520)).save(str(SORTIE / "arbre.png"))
    blanc_vers_transparent(reduire(source.copy(ZONE_LOGO), 520)).save(str(SORTIE / "logo.png"))
    lavis().save(str(SORTIE / "lavis.png"))
    print(f"Images générées dans {SORTIE}")


if __name__ == "__main__":
    main()
