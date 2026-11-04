"""Étiquettes « feuille », onglets soulignés, champ de recherche et disposition fluide."""

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
    QWidgetItem,
)

from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.widgets import ClickableFrame


class FlowLayout(QLayout):
    """Place les widgets en ligne et passe à la ligne quand la place manque."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._spacing = spacing
        self.setContentsMargins(QMargins(0, 0, 0, 0))

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def addWidget(self, widget: QWidget) -> None:
        self.addChildWidget(widget)
        self.addItem(QWidgetItem(widget))

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _arrange(self, rect: QRect, apply: bool) -> int:
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line_height > 0:
                x = rect.x()
                y += line_height + self._spacing
                line_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


class LeafChip(ClickableFrame):
    """Étiquette en forme de feuille.

    `kind` : « filled » (mot partagé avec un autre récit), « outline » (mot propre
    à ce récit), « proposed » (proposé par l'analyse, à valider), « add » (ajouter).
    """

    closed = Signal()

    def __init__(
        self,
        text: str,
        kind: str = "filled",
        small: bool = False,
        closable: bool = False,
        clickable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(f"leaf_{kind}{'_small' if small else ''}", parent)
        if not clickable:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(self)
        row.setContentsMargins(
            12, 3, 12 if not closable else 4, 3
        ) if small else row.setContentsMargins(14, 5, 14 if not closable else 6, 5)
        row.setSpacing(4)
        self.text_label = QLabel(text)
        self.text_label.setFont(theme.font(theme.SANS, 13 if small else 15))
        colors = {
            "filled": theme.LEAF_TEXT,
            "outline": theme.CHIP_OUTLINE_TEXT,
            "proposed": theme.NAV_MUTED,
            "add": theme.NAV_MUTED,
        }
        self.text_label.setStyleSheet(f"color: {colors.get(kind, theme.INK)};")
        row.addWidget(self.text_label)
        if closable:
            close = QToolButton()
            close.setObjectName("chipClose")
            close.setText("×")
            close.setCursor(Qt.CursorShape.PointingHandCursor)
            close.setAccessibleName(f"Retirer {text}")
            close.setToolTip("Retirer ce mot")
            close.clicked.connect(self.closed)
            row.addWidget(close)


class UnderlineTab(QPushButton):
    """Onglet souligné de rouge quand il est actif."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("tab")
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        bold = QFontMetrics(theme.font(theme.SANS, 15, QFont.Weight.DemiBold))
        self.setMinimumWidth(bold.horizontalAdvance(text) + 32)


class SearchField(QLineEdit):
    """Champ de recherche souligné, en italique."""

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("search")
        self.setPlaceholderText(placeholder)
        self.setFont(theme.font(theme.SERIF, 18, italic=True))
        self.setClearButtonEnabled(True)
        self.setAccessibleName(placeholder)


class ElidedLabel(QLabel):
    """Libellé sur une ligne, coupé par « … » s'il est trop long."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        metrics = QFontMetrics(self.font())
        self.setText(metrics.elidedText(self._full, Qt.TextElideMode.ElideRight, self.width()))
