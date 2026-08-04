"""NavigationManager managing page stack indices and routing between views."""

from typing import Dict, Optional
from PySide6.QtWidgets import QStackedWidget, QWidget
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_navigation")


class NavigationManager:
    """Manages page routing and active view indices on QStackedWidget."""

    def __init__(self, stacked_widget: QStackedWidget) -> None:
        self.stacked_widget = stacked_widget
        self.pages: Dict[str, int] = {}

    def register_page(self, page_id: str, widget: QWidget) -> int:
        """Registers a view widget with a page_id string."""
        idx = self.stacked_widget.addWidget(widget)
        self.pages[page_id] = idx
        logger.info(f"Registered GUI view '{page_id}' at index {idx}.")
        return idx

    def navigate_to(self, page_id: str) -> bool:
        """Navigates to the registered page_id view."""
        if page_id in self.pages:
            idx = self.pages[page_id]
            self.stacked_widget.setCurrentIndex(idx)
            logger.info(f"Navigated GUI to page '{page_id}' (index={idx}).")
            return True
        logger.warning(f"Could not navigate to unknown page '{page_id}'.")
        return False

    def get_active_page(self) -> Optional[str]:
        """Returns active page_id string."""
        curr_idx = self.stacked_widget.currentIndex()
        for pid, idx in self.pages.items():
            if idx == curr_idx:
                return pid
        return None
