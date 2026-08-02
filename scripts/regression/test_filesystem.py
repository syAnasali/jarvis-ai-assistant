import time
from app.services.filesystem.policy import FilesystemPolicy
from app.services.filesystem.resolver import FilesystemResolver
from app.services.filesystem.service import FilesystemService
from app.config.settings import settings

def run_regression() -> dict:
    start_time = time.perf_counter()
    try:
        policy = FilesystemPolicy()
        resolver = FilesystemResolver(policy)
        service = FilesystemService(
            policy=policy,
            resolver=resolver,
            list_max_entries=settings.filesystem_list_max_entries,
            write_max_chars=settings.filesystem_write_max_chars,
            relative_path_max_length=settings.filesystem_relative_path_max_length
        )
        
        # Test path resolution safety using resolver (checking exists boolean attribute)
        resolved = resolver.resolve("workspace", "app")
        if not resolved.exists:
            raise ValueError(f"Resolved path does not exist: {resolved.absolute_path}")
            
        # Test non-recursive directory listing
        entries = service.list_directory("workspace", ".")
        if not entries:
            raise ValueError("Filesystem listing returned empty results for workspace root.")
            
        duration = time.perf_counter() - start_time
        return {
            "name": "test_filesystem.py",
            "status": "PASS",
            "duration": duration,
            "reason": "Filesystem sandbox path resolution and listing verified successfully."
        }
    except Exception as e:
        duration = time.perf_counter() - start_time
        return {
            "name": "test_filesystem.py",
            "status": "FAIL",
            "duration": duration,
            "reason": f"Filesystem test failed: {e}"
        }
