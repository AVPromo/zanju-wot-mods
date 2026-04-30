# Research Progress Bar UI

This folder contains the live garage SWF for the mod.

Current scope:

- top-of-screen garage research bar
- basic-research-only progress fill (combat XP + free XP)
- typed research markers with one-letter labels
- right-side combat-only and combat-plus-free percentage counters
- per-marker XP labels under the bar
- default-garage-only visibility, with hiding for loadout/setup screens and other non-default hangar routes
- public ActionScript callbacks for Python view wiring

Build the SWF with:

```powershell
powershell -ExecutionPolicy Bypass -File .\mods\research-progress-bar\ui-src\compile_ui.ps1
```

Output path:

- `mods/research-progress-bar/res/gui/flash/research-progress-bar-lobby.swf`

Notes:

- The live in-game garage widget uses this custom SWF path.
- The Python side keeps the `SFWindow` loaded and toggles SWF visibility for supported hide/show cases instead of destroying and reloading it for transient popups.
- Runtime toggles live in `mods/research-progress-bar/config/config.json`.
- `scaleformPrototypeEnabled` controls the active custom SWF path.
- The custom SWF root must extend a WoT `IView`-compatible class such as `net.wg.infrastructure.base.AbstractView`; a plain `Sprite` root is rejected by the loader.
- The local compile path uses a tiny external stub SWC for `AbstractView` so `mxmlc` can build without bundled WG source/SWCs.
- The exposed ActionScript callbacks used by the Python view wiring are:
  - `as_ping()`
  - `as_setProgress(number)`
  - `as_setContext(object)`
  - `as_setVisible(boolean)`