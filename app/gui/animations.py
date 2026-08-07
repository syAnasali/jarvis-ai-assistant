"""PageTransitionManager rendering smooth QGraphicsOpacityEffect cross-fade animations."""

from typing import Optional
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QObject


class PageTransitionManager(QObject):
    """Orchestrates smooth cross-fade page transition animations between QStackedWidget views."""

    def __init__(self, stacked_widget: QStackedWidget, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.stacked_widget = stacked_widget
        self.current_anim: Optional[QPropertyAnimation] = None

    def fade_to_index(self, index: int, duration_ms: int = 150) -> None:
        """Cross-fades to the specified view index."""
        if index < 0 or index >= self.stacked_widget.count():
            return

        target_widget = self.stacked_widget.widget(index)
        if not target_widget:
            return

        effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(effect)

        self.stacked_widget.setCurrentIndex(index)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.current_anim = anim
        anim.start()
