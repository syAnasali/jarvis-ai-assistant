"""Windows application launch service."""

import os
import subprocess
import logging
from typing import Dict, Any
from app.services.applications.models import InstalledApplication
from app.core.exceptions import ToolExecutionError

logger = logging.getLogger("application_launcher")

class ApplicationLauncher:
    """Safely launches resolved Windows applications."""

    def launch(self, app: InstalledApplication) -> Dict[str, Any]:
        """Launches the specified application.

        Args:
            app: The InstalledApplication instance to launch.

        Returns:
            Dict[str, Any]: Launch metadata (application_id, name, launched, pid).

        Raises:
            ToolExecutionError: If validation or process creation fails.
        """
        # 1. Verify model validity
        if not isinstance(app, InstalledApplication):
            raise ToolExecutionError("Invalid application model provided.")

        # 2. Verify executable path exists and is a regular file
        path = app.executable_path
        if not path:
            raise ToolExecutionError("Application executable path is empty.")
            
        if not os.path.exists(path):
            raise ToolExecutionError(f"Application executable not found at: '{path}'")
            
        if not os.path.isfile(path):
            raise ToolExecutionError(f"Application target is not a file: '{path}'")

        # 3. Verify file extension is allowed (.exe or .com)
        _, ext = os.path.splitext(path.lower())
        if ext not in ('.exe', '.com'):
            raise ToolExecutionError(
                f"Application launcher blocked execution: extension '{ext}' is not allowed. "
                "Only '.exe' and '.com' executables are supported."
            )

        # 4. Safe process launch
        logger.info(f"Launching application: ID={app.application_id} name='{app.name}' path='{path}'")
        try:
            # Launch in background, detached from main process console
            # We do not use shell=True, and we do not pass user arguments.
            process = subprocess.Popen(
                [path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            return {
                "application_id": app.application_id,
                "name": app.name,
                "launched": True,
                "pid": process.pid
            }
        except Exception as e:
            logger.error(f"Failed to launch application '{app.name}': {e}")
            raise ToolExecutionError(f"System failed to start the application: {e}")
