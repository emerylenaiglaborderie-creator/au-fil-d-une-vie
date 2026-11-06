"""Tracés à l'encre partagés : courbes de Bézier, splines lissées, traits effilés.

Servent aux racines de l'arbre d'accueil et aux rameaux décoratifs des pages.
"""

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath


def bezier(p0: QPointF, c1: QPointF, c2: QPointF, p3: QPointF, t: float) -> QPointF:
    u = 1 - t
    return p0 * (u**3) + c1 * (3 * u * u * t) + c2 * (3 * u * t * t) + p3 * (t**3)


def smooth_path(points: list[QPointF]) -> QPainterPath:
    """Courbe lisse passant par tous les points (spline de Catmull-Rom)."""
    path = QPainterPath(points[0])
    padded = [points[0], *points, points[-1]]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        path.cubicTo(p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6, p2)
    return path


def tapered_path(centre: QPainterPath, start_width: float, end_width: float) -> QPainterPath:
    """Trait plein qui s'affine le long d'un chemin quelconque."""
    steps = 90
    total = centre.length()
    left: list[QPointF] = []
    right: list[QPointF] = []
    for i in range(steps + 1):
        t = i / steps
        percent = centre.percentAtLength(total * t)
        point = centre.pointAtPercent(percent)
        angle = math.radians(centre.angleAtPercent(percent))
        normal = QPointF(
            math.sin(angle), math.cos(angle)
        )  # angle de Qt : sens trigonométrique, y vers le bas
        width = end_width + (start_width - end_width) * (1 - t) ** 1.6
        left.append(point + normal * (width / 2))
        right.append(point - normal * (width / 2))
    path = QPainterPath(left[0])
    for point in left[1:]:
        path.lineTo(point)
    path.quadTo(centre.pointAtPercent(1.0), right[-1])
    for point in reversed(right[:-1]):
        path.lineTo(point)
    path.closeSubpath()
    return path


def leaf_path(base: QPointF, angle: float, length: float, width: float) -> QPainterPath:
    """Feuille en amande, de sa base vers sa pointe, orientée selon un angle (degrés).

    L'angle suit la convention de l'écran : 0 vers la droite, 90 vers le bas.
    """
    a = math.radians(angle)
    along = QPointF(math.cos(a), math.sin(a))
    across = QPointF(-along.y(), along.x())
    tip = base + along * length
    belly = base + along * (length * 0.45)
    path = QPainterPath(base)
    path.quadTo(belly + across * width, tip)
    path.quadTo(belly - across * (width * 0.85), base)
    path.closeSubpath()
    return path


def leaf_vein(base: QPointF, angle: float, length: float) -> QPainterPath:
    """Nervure centrale, légèrement courbe, qui s'arrête avant la pointe."""
    a = math.radians(angle)
    along = QPointF(math.cos(a), math.sin(a))
    across = QPointF(-along.y(), along.x())
    path = QPainterPath(base)
    path.quadTo(base + along * (length * 0.45) + across * 1.5, base + along * (length * 0.82))
    return path
