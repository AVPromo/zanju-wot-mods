# Research Progress Bar UI Prototype

This folder contains the first free-toolchain garage UI prototype for the mod.

Current scope:

- draggable garage panel
- text labels for vehicle and summary lines
- graphical progress bar
- placeholder icon strip
- public ActionScript callbacks for Python view wiring

Build the SWF with:

```powershell
powershell -ExecutionPolicy Bypass -File .\mods\research-progress-bar\ui-src\compile_ui.ps1
```

Output path:

- `mods/research-progress-bar/res/gui/flash/research-progress-bar-lobby.swf`

Notes:

- The current Python `GUI.Text` overlay remains the active/debug UI.
- The live in-game garage prototype now uses this custom SWF path.
- Runtime toggles live in `mods/research-progress-bar/config/config.json`.
- `scaleformPrototypeEnabled` controls the active custom SWF prototype.
- The custom SWF root must extend a WoT `IView`-compatible class such as `net.wg.infrastructure.base.AbstractView`; a plain `Sprite` root is rejected by the loader.
- The local compile path uses a tiny external stub SWC for `AbstractView` so `mxmlc` can build without bundled WG source/SWCs.
- The exposed ActionScript callbacks used by the Python view wiring are:
  - `as_ping()`
  - `as_setProgress(number)`
  - `as_setContext(object)`