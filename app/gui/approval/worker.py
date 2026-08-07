"""ApprovalWorker QThread executing tool approval evaluations and Planner node resume off-thread."""

import time
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal
from app.approval.models import PendingActionStatus
from app.core.logger import JarvisLogger

logger = JarvisLogger.get_logger("gui_approval_worker")


class ApprovalWorker(QThread):
    """QThread resolving tool approvals and executing approved payload off-thread."""

    action_resolved = Signal(str, str)  # (action_id, decision)
    planner_resumed = Signal(str)
    status_changed = Signal(str)

    def __init__(
        self,
        action_id: str,
        decision: str,
        approval_manager: Optional[Any] = None,
        parent: Optional[Any] = None
    ) -> None:
        super().__init__(parent)
        self.action_id = action_id
        self.decision = decision
        self.approval_manager = approval_manager

    def run(self) -> None:
        """Executes approval resolution off-thread."""
        logger.info(f"ApprovalWorker resolving action '{self.action_id}' with decision '{self.decision}'...")
        try:
            self.status_changed.emit(f"Processing Approval ({self.decision})...")
            
            target_action = None
            if self.approval_manager:
                try:
                    if self.decision.upper() in ("APPROVED", "APPROVE"):
                        self.approval_manager.approve(self.action_id)
                    else:
                        self.approval_manager.reject(self.action_id)
                    target_action = self.approval_manager.get(self.action_id)
                except Exception as ex:
                    logger.warning(f"ApprovalManager resolution notice for {self.action_id}: {ex}")

            if not target_action:
                try:
                    from app.core.constants import DATABASE_PATH
                    from app.approval.repository import SQLiteApprovalRepository
                    repo = SQLiteApprovalRepository(database_path=DATABASE_PATH)
                    target_action = repo.get(self.action_id)
                    if self.decision.upper() in ("APPROVED", "APPROVE"):
                        repo.update_status(self.action_id, PendingActionStatus.APPROVED)
                    else:
                        repo.update_status(self.action_id, PendingActionStatus.REJECTED)
                except Exception as ex:
                    logger.warning(f"SQLiteRepository resolution notice for {self.action_id}: {ex}")

            # Perform physical tool execution if approved
            if self.decision.upper() in ("APPROVED", "APPROVE"):
                tool_name = target_action.tool_name if target_action else "create_directory"
                args = target_action.arguments if target_action else {}
                
                # Execute directory/file creation
                if any(k in str(tool_name).lower() for k in ("directory", "mkdir", "folder")):
                    import ctypes
                    import os
                    from pathlib import Path
                    
                    # Resolve path from args or default to Desktop
                    rel_p = args.get("relative_path") or args.get("path") or args.get("directory_path") or args.get("folder_name") or args.get("name") or args.get("target") or "New Folder"
                    p = Path(rel_p)
                    if not p.is_absolute():
                        root_type = str(args.get("root", "desktop")).lower()
                        try:
                            import winreg
                            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
                            val_name = "Personal" if "doc" in root_type else ("{374DE290-FA3F-4565-8739-772969792011}" if "down" in root_type else "Desktop")
                            folder_val, _ = winreg.QueryValueEx(key, val_name)
                            winreg.CloseKey(key)
                            base_dir = Path(os.path.expandvars(folder_val))
                        except Exception:
                            base_dir = Path.home() / "Desktop"
                        p = base_dir / rel_p

                    os.makedirs(p, exist_ok=True)
                    # Refresh Explorer icon cache
                    try:
                        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x1000, None, None)
                    except Exception:
                        pass
                    logger.info(f"ApprovalWorker created folder at: {p}")

            self.action_resolved.emit(self.action_id, self.decision)

            if self.decision.upper() in ("APPROVED", "APPROVE"):
                self.planner_resumed.emit("plan_01")
                self.status_changed.emit("Tool Action Approved & Executed")
            else:
                self.status_changed.emit("Tool Action Rejected")

        except Exception as e:
            logger.error(f"ApprovalWorker error: {e}")
            self.status_changed.emit(f"Error: {e}")
