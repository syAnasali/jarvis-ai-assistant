# Production Polish & UX Refinement Specification (`app/gui/`)

## Overview

The **Production Polish & UX Refinement** phase upgrades the entire PySide6 Desktop GUI experience for production readiness.

It introduces global keyboard productivity (`Ctrl+Shift+P` Command Palette), smooth `QGraphicsOpacityEffect` page transition cross-fades, application-wide hotkeys, layout and draft session auto-restoration, high-DPI display scaling, and an expanded 5-tab settings workspace while reusing existing backend logic without duplication.

---

## Architectural & UX Modules Added

```
app/gui/
├── command_palette.py  # CommandPaletteDialog (Ctrl+Shift+P quick action launcher)
├── animations.py       # PageTransitionManager (Smooth QGraphicsOpacityEffect cross-fades)
├── shortcuts.py        # GlobalShortcutManager (Application-wide hotkeys)
├── session.py          # SessionRestoreManager (Auto-save drafts & layout restoration)
└── views/
    └── settings_view.py # Expanded 5-tab SettingsView workspace
```

---

## Component Responsibilities

1. **`command_palette.py` (`CommandPaletteDialog`)**: Popup dialog triggered via `Ctrl+Shift+P` allowing instant keyboard navigation to any registered view (Chat, Planner, Memory, Knowledge, Vision, Voice, Plugins, Diagnostics, Settings) and fast action execution.
2. **`animations.py` (`PageTransitionManager`)**: Applies smooth `QGraphicsOpacityEffect` cross-fade animations between views when switching sidebar pages or using the command palette.
3. **`shortcuts.py` (`GlobalShortcutManager`)**: Binds global keyboard hotkeys (`Ctrl+Shift+P` for Command Palette, `Ctrl+T` for Theme Toggle, `F11` for Fullscreen, `Ctrl+Comma` for Settings).
4. **`session.py` (`SessionRestoreManager`)**: Auto-saves active view state, window geometry, scroll position, and unsaved input drafts via `QSettings`, restoring them on application startup.
5. **`views/settings_view.py` (`SettingsView`)**: Expands settings into 5 tabbed sections:
   - **🎨 Appearance**: Theme selector (Dark/Light HSL), font scaling, accent colors, High-DPI scaling.
   - **⚙️ Behavior**: Session auto-restore, system tray minimization, native notifications.
   - **🎙️ Voice & Vision**: Microphone selector, wake-word sensitivity, screen capture resolution.
   - **🔒 Plugins & Privacy**: Permission sandboxing, telemetry retention policies.
   - **🚀 Performance**: Worker thread pool sizing, RAG vector cache limits.

---

## Global Hotkeys Reference

| Shortcut | Action |
|---|---|
| `Ctrl+Shift+P` | Opens Command Palette popup dialog |
| `Ctrl+T` | Toggles Dark/Light mode theme |
| `F11` | Toggles Fullscreen window mode |
| `Ctrl+Comma` | Navigates to Settings workspace |
