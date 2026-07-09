"""Windows application discovery and resolution."""

import os
import re
import logging
from typing import Dict, Any, List, Set, Tuple
from app.services.applications.models import InstalledApplication
from app.config.settings import settings

logger = logging.getLogger("application_resolver")

# Centralized built-in mapping
BUILT_IN_APPLICATIONS = {
    "notepad": {
        "name": "Notepad",
        "executable_path": r"%SystemRoot%\System32\notepad.exe",
        "version": "Built-in",
        "publisher": "Microsoft Corporation",
        "aliases": ["notepad", "editor"]
    },
    "calculator": {
        "name": "Calculator",
        "executable_path": r"%SystemRoot%\System32\calc.exe",
        "version": "Built-in",
        "publisher": "Microsoft Corporation",
        "aliases": ["calc", "calculator"]
    }
}

# Centralized aliases map (maps alias key -> canonical lowercased application name or alias target name)
ALIASES = {
    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "visual studio code": "visual studio code",
    "calc": "calculator",
    "calculator": "calculator",
    "notepad": "notepad"
}

class ApplicationResolution:
    """Represents the outcome of a resolved application query."""
    def __init__(
        self,
        query: str,
        status: str,
        application: InstalledApplication | None = None,
        candidates: List[InstalledApplication] = None,
        match_type: str | None = None
    ) -> None:
        self.query = query
        self.status = status
        self.application = application
        self.candidates = candidates or []
        self.match_type = match_type

class ApplicationResolver:
    """Discovers installed Windows applications and resolves user queries."""
    
    def __init__(self) -> None:
        self._cached_apps: Dict[str, InstalledApplication] = {}
        
    def discover_all(self, force_refresh: bool = False) -> List[InstalledApplication]:
        """Discovers and deduplicates all launchable applications."""
        if self._cached_apps and not force_refresh:
            return list(self._cached_apps.values())
            
        discovered: Dict[str, InstalledApplication] = {}
        
        # 1. Fetch versions/publishers from Uninstall registry
        from app.tools.builtin.applications import discover_installed_applications
        uninstall_info = {}
        try:
            for app_meta in discover_installed_applications():
                name = app_meta.get("name", "").strip()
                if name:
                    uninstall_info[name.lower()] = (app_meta.get("version", ""), app_meta.get("publisher", ""))
        except Exception as e:
            logger.error(f"Failed to scan Uninstall registry: {e}")
            
        def get_uninstall_metadata(app_name: str) -> Tuple[str, str]:
            app_name_lower = app_name.lower()
            # Try exact match first
            if app_name_lower in uninstall_info:
                return uninstall_info[app_name_lower]
            # Try substring match
            for k, v in uninstall_info.items():
                if k in app_name_lower or app_name_lower in k:
                    return v
            return ("", "")

        # 2. Load built-in applications
        for key, info in BUILT_IN_APPLICATIONS.items():
            path = os.path.normpath(os.path.expandvars(info["executable_path"]))
            if os.path.isfile(path):
                app = InstalledApplication(
                    name=info["name"],
                    executable_path=path,
                    version=info["version"],
                    publisher=info["publisher"],
                    source="Built-in",
                    metadata={"aliases": info["aliases"]}
                )
                discovered[app.executable_path.lower()] = app
                
        # 3. Discover from App Paths registry
        app_paths = self._discover_app_paths()
        for name, path in app_paths:
            # We enforce max discovery entries check
            if len(discovered) >= settings.application_discovery_max_entries:
                break
            norm_path = os.path.normpath(os.path.expandvars(path.strip(' \t\n\r"\'')))
            if not os.path.isfile(norm_path):
                continue
                
            clean_name = os.path.splitext(name)[0]  # E.g. Code.exe -> Code
            version, publisher = get_uninstall_metadata(clean_name)
            
            app = InstalledApplication(
                name=clean_name,
                executable_path=norm_path,
                version=version,
                publisher=publisher,
                source="App Paths"
            )
            
            # Deduplicate: prefer Start Menu over App Paths if path already exists
            path_key = app.executable_path.lower()
            if path_key not in discovered:
                discovered[path_key] = app
                
        # 4. Discover from Start Menu shortcuts
        shortcuts = self._discover_start_menu_shortcuts()
        for shortcut_name, target_path in shortcuts:
            if len(discovered) >= settings.application_discovery_max_entries:
                break
            norm_path = os.path.normpath(os.path.expandvars(target_path.strip(' \t\n\r"\'')))
            if not os.path.isfile(norm_path):
                continue
                
            # Filter extensions
            ext = os.path.splitext(norm_path.lower())[1]
            if ext not in ('.exe', '.com'):
                continue
                
            version, publisher = get_uninstall_metadata(shortcut_name)
            
            app = InstalledApplication(
                name=shortcut_name,
                executable_path=norm_path,
                version=version,
                publisher=publisher,
                source="Start Menu"
            )
            
            # Deduplicate: Start Menu overrides App Paths because names are nicer
            path_key = app.executable_path.lower()
            discovered[path_key] = app
            
        # Extra deduplication by name (preferring Built-in > Start Menu > App Paths)
        name_dedup: Dict[str, InstalledApplication] = {}
        source_priority = {"App Paths": 1, "Start Menu": 2, "Built-in": 3}
        for app in discovered.values():
            name_key = app.name.lower()
            if name_key in name_dedup:
                existing = name_dedup[name_key]
                p1 = source_priority.get(existing.source, 0)
                p2 = source_priority.get(app.source, 0)
                # Keep the higher priority one, or if equal, keep the one with shorter path
                if p2 > p1:
                    name_dedup[name_key] = app
                elif p2 == p1:
                    if len(app.executable_path) < len(existing.executable_path):
                        name_dedup[name_key] = app
            else:
                name_dedup[name_key] = app
                
        final_discovered = {app.executable_path.lower(): app for app in name_dedup.values()}
        self._cached_apps = final_discovered
        return list(final_discovered.values())
        
    def _discover_app_paths(self) -> List[Tuple[str, str]]:
        """Reads App Paths subkeys from registry."""
        results = []
        try:
            import winreg
        except ImportError:
            return results
            
        targets = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]
        
        for hkey, subkey_path in targets:
            for access in [winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ | winreg.KEY_WOW64_32KEY]:
                try:
                    key = winreg.OpenKey(hkey, subkey_path, 0, access)
                except OSError:
                    continue
                    
                try:
                    info = winreg.QueryInfoKey(key)
                    subkeys_count = info[0]
                    for i in range(subkeys_count):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    path_val, _ = winreg.QueryValueEx(subkey, "")
                                    if path_val:
                                        results.append((subkey_name, str(path_val)))
                                except OSError:
                                    pass
                        except OSError:
                            continue
                except OSError:
                    pass
                finally:
                    winreg.CloseKey(key)
        return results

    def _discover_start_menu_shortcuts(self) -> List[Tuple[str, str]]:
        """Walks Start Menu Program directories and parses .lnk files."""
        results = []
        
        # Get start menu dirs
        start_menu_dirs = []
        all_users = os.environ.get("ALLUSERSPROFILE")
        appdata = os.environ.get("APPDATA")
        
        if all_users:
            start_menu_dirs.append(os.path.join(all_users, r"Microsoft\Windows\Start Menu\Programs"))
        if appdata:
            start_menu_dirs.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
            
        # Fallbacks
        if not all_users:
            start_menu_dirs.append(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs")
            
        from app.services.applications.lnk_parser import resolve_lnk_binary
        
        for root_dir in start_menu_dirs:
            if not os.path.isdir(root_dir):
                continue
                
            for dirpath, _, filenames in os.walk(root_dir):
                for filename in filenames:
                    if filename.lower().endswith('.lnk'):
                        full_lnk_path = os.path.join(dirpath, filename)
                        target = resolve_lnk_binary(full_lnk_path)
                        if target:
                            shortcut_name = os.path.splitext(filename)[0]
                            results.append((shortcut_name, target))
        return results

    def get_by_id(self, application_id: str) -> InstalledApplication | None:
        """Retrieves a discovered application by its ID."""
        apps = self.discover_all()
        for app in apps:
            if app.application_id == application_id:
                return app
        return None

    def resolve(self, query: str) -> ApplicationResolution:
        """Resolves a user query using deterministic matching hierarchy."""
        query_clean = query.strip()
        if not query_clean:
            return ApplicationResolution(query, "NOT_FOUND")
            
        apps = self.discover_all()
        query_norm = query_clean.lower()
        
        # Expand alias if any
        target_canonical = ALIASES.get(query_norm, query_norm)
        
        # Helper to sort candidates deterministically
        def sort_apps(candidates: List[InstalledApplication]) -> List[InstalledApplication]:
            return sorted(candidates, key=lambda x: (x.name.lower(), x.executable_path.lower()))

        # Level 1: Exact normalized name match
        exact_name_matches = []
        for app in apps:
            if app.name.lower() == query_norm:
                exact_name_matches.append(app)
        
        if exact_name_matches:
            unique_matches = {a.application_id: a for a in exact_name_matches}
            sorted_unique = sort_apps(list(unique_matches.values()))
            if len(sorted_unique) == 1:
                return ApplicationResolution(query, "RESOLVED", sorted_unique[0], match_type="exact_name")
            else:
                return ApplicationResolution(
                    query,
                    "AMBIGUOUS",
                    candidates=sorted_unique[:settings.application_resolution_max_candidates],
                    match_type="exact_name"
                )

        # Level 2: Exact alias match
        exact_alias_matches = []
        for app in apps:
            app_aliases = app.metadata.get("aliases", [])
            app_aliases_lower = [a.lower() for a in app_aliases]
            if target_canonical in app_aliases_lower or query_norm in app_aliases_lower:
                exact_alias_matches.append(app)
                
        if exact_alias_matches:
            unique_matches = {a.application_id: a for a in exact_alias_matches}
            sorted_unique = sort_apps(list(unique_matches.values()))
            if len(sorted_unique) == 1:
                return ApplicationResolution(query, "RESOLVED", sorted_unique[0], match_type="exact_alias")
            else:
                return ApplicationResolution(
                    query,
                    "AMBIGUOUS",
                    candidates=sorted_unique[:settings.application_resolution_max_candidates],
                    match_type="exact_alias"
                )

        # Level 3: Prefix match
        prefix_matches = []
        for app in apps:
            app_name_lower = app.name.lower()
            if app_name_lower.startswith(query_norm) or app_name_lower.startswith(target_canonical):
                prefix_matches.append(app)
                
        if prefix_matches:
            unique_matches = {a.application_id: a for a in prefix_matches}
            sorted_unique = sort_apps(list(unique_matches.values()))
            if len(sorted_unique) == 1:
                return ApplicationResolution(query, "RESOLVED", sorted_unique[0], match_type="prefix")
            else:
                return ApplicationResolution(
                    query,
                    "AMBIGUOUS",
                    candidates=sorted_unique[:settings.application_resolution_max_candidates],
                    match_type="prefix"
                )

        # Level 4: Substring match
        substring_matches = []
        for app in apps:
            app_name_lower = app.name.lower()
            if query_norm in app_name_lower or target_canonical in app_name_lower:
                substring_matches.append(app)
                
        if substring_matches:
            unique_matches = {a.application_id: a for a in substring_matches}
            sorted_unique = sort_apps(list(unique_matches.values()))
            if len(sorted_unique) == 1:
                return ApplicationResolution(query, "RESOLVED", sorted_unique[0], match_type="substring")
            else:
                return ApplicationResolution(
                    query,
                    "AMBIGUOUS",
                    candidates=sorted_unique[:settings.application_resolution_max_candidates],
                    match_type="substring"
                )

        return ApplicationResolution(query, "NOT_FOUND")
