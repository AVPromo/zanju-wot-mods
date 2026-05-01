# Research Progress Bar UI

This folder contains the source and compiler entrypoint for the garage SWF used by the mod.

Current scope:

- top-of-screen garage research bar
- basic-research-only progress fill (combat XP + free XP)
- typed research markers with one-letter labels
- right-side combat-only and combat-plus-free percentage counters
- per-marker XP labels under the bar
- default-garage-only visibility, with hiding for loadout/setup screens and other non-default hangar routes
- public ActionScript callbacks for Python view wiring

Canonical UI build entrypoint:

```powershell
python .\mods\research-progress-bar\ui-src\compile_ui.py
```

Output path:

- `mods/research-progress-bar/ui-src/build/res/gui/flash/research-progress-bar-lobby.swf`

Notes:

- The live in-game garage widget still loads `res/gui/flash/research-progress-bar-lobby.swf` inside the final `.wotmod`; `build.py` stages the generated SWF into that archive path during packaging.
- `build.py research-progress-bar` and `dev_test_cycle.py research-progress-bar` now invoke `ui-src/compile_ui.py` automatically before packaging, so manual UI builds are mainly for faster SWF-only iteration.
- Files under `ui-src/build/` are generated artifacts and should not be committed.
- The final user-facing release bundle is emitted under `dist/` with the `.wotmod`, copied config, and install README.
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