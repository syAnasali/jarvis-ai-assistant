import time
from app.services.desktop.policy import DesktopPolicy
from app.services.desktop.resolver import DesktopResolver
from app.services.desktop.service import DesktopService
from app.config.settings import settings

def run_regression() -> dict:
    start_time = time.perf_counter()
    try:
        desktop_policy = DesktopPolicy()
        desktop_resolver = DesktopResolver()
        service = DesktopService(
            policy=desktop_policy,
            resolver=desktop_resolver,
            list_limit=settings.desktop_window_list_limit,
            text_max_chars=settings.desktop_text_max_chars
        )
        
        # Test visible windows enumeration (should execute safely on any machine)
        windows = service.list_visible_windows()
        
        duration = time.perf_counter() - start_time
        return {
            "name": "test_desktop.py",
            "status": "PASS",
            "duration": duration,
            "reason": f"Desktop service window enumeration successful. Found {len(windows)} visible windows."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_desktop.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Desktop test failed: {e}"
        }
