"""SessionRestoreManager persisting active view states, window geometry, and drafts."""

from typing import Dict, Optional
from PySide6.QtCore import QSettings


class SessionRestoreManager:
    """Persists and restores active session layout, geometry, and input drafts."""

    def __init__(self, organization: str = "JarvisAI", application: str = "JarvisDesktopSession") -> None:
        self.settings = QSettings(organization, application)

    def save_session(self, active_page: str, draft_text: str = "") -> None:
        """Saves current session state."""
        self.settings.setValue("session/active_page", active_page)
        self.settings.setValue("session/draft_text", draft_text)

    def restore_active_page(self, default_page: str = "chat") -> str:
        """Restores last active page name."""
        return str(self.settings.value("session/active_page", default_page))

    def restore_draft_text(self) -> str:
        """Restores unsaved chat input draft."""
        return str(self.settings.value("session/draft_text", ""))
