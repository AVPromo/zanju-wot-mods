# Zanju's Research Progress Bar UI

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
python .\mods\research-progress-bar\ui\compile_ui.py
```

Output path:

- `mods/research-progress-bar/ui/build/res/gui/flash/research-progress-bar-lobby.swf`

Notes:

- The live in-game garage widget still loads `res/gui/flash/research-progress-bar-lobby.swf` inside the final `.wotmod`; `wot_mods_build` stages the generated SWF into that archive path during packaging.
- `wot_mods_build research-progress-bar` and `wot_mods_cycle research-progress-bar` now invoke `ui/compile_ui.py` automatically before packaging, so manual UI builds are mainly for faster SWF-only iteration.
- Files under `ui/build/` are generated artifacts and should not be committed.
- The final user-facing release bundle is emitted under `dist/` with the `.wotmod`, copied config, and install README.
- The Python side now registers an optional `ModsSettingsAPI` template for `enabled`, `Research`, `Field Mods`, `Upgrades`, and `Elite`; the Elite control is a radio group with `On`, `Customization only`, and `Off`.
- Runtime localization now reads `mods/configs/research-progress-bar/i18n/<language>.yml` with English fallback; authored `mods/research-progress-bar/i18n/*.yml` files are staged both into the packaged mod text resources and into the deployed config `i18n/` folder.
- That in-game settings path is additive only: if `ModsSettingsAPI`, `ModsListAPI`, or `OpenWG Gameface` is missing, the mod should keep working from `mods/configs/research-progress-bar/config.json` without crashing.
- Changes made through the in-game configurator are persisted back to `mods/configs/research-progress-bar/config.json` so manual edits and UI edits stay on the same config path.
- The Python side keeps the `SFWindow` loaded and toggles SWF visibility for supported hide/show cases instead of destroying and reloading it for transient popups.
- Repository config source lives in `mods/research-progress-bar/config.json` and ships to `mods/configs/research-progress-bar/config.json`.
- `scaleformPrototypeEnabled` controls the active custom SWF path.
- The custom SWF root must extend a WoT `IView`-compatible class such as `net.wg.infrastructure.base.AbstractView`; a plain `Sprite` root is rejected by the loader.
- The local compile path builds a tiny external WoT API mirror SWC for `AbstractView` so `mxmlc` can compile without bundled WG source/SWCs.
- The UI tree is intentionally flat: keep the main `.as` entrypoint at `ui/`, the compile-time WoT API mirror under `ui/wot-api/`, shared UI helpers as flat siblings, and embedded assets under `ui/assets/` including `ui/assets/fonts/` for vendored fonts.

Current source split:

- `ResearchProgressBarLobby.as`: WoT-facing `AbstractView` root; lifecycle bridge plus high-level payload application.
- `ResearchProgressBarViewFactory.as`: build-time display-object creation for bars, masks, counters, and tooltip shell.
- `ResearchProgressBarStageSupport.as`: stage listener wiring, tracked-size detection, and bar-layout resolution.
- `ResearchProgressBarViewState.as`: mode resolution, selected-mode sync, and fill-state selection.
- `ResearchProgressBarBars.as`: bar visibility, bitmap bounds, and fill-mask drawing.
- `ResearchProgressBarCounterFields.as`: counter text selection and text-format application.
- `ResearchProgressBarCounterLayout.as`: counter positioning around and below the bar.
- `ResearchProgressBarModes.as`: mode normalization and mode-button rendering.
- `ResearchProgressBarInteractions.as`: mode-button click resolution and marker rebuild/clear glue.
- `ResearchProgressBarMarkers.as`: marker display creation, hit areas, and tooltip payload mapping.
- `ResearchProgressBarTooltipView.as`: tooltip hit-testing, show/hide behavior, and stage clamping.
- `ResearchProgressBarTooltipContent.as`: tooltip section and text rendering.
- `ResearchProgressBarFonts.as`: embedded font registration plus shared text-field setup for tooltip, marker, mode-button, and counter text.
- `ResearchProgressBarMarkerAssets.as`: bar-icon bitmap lookup for typed markers.
- `ResearchProgressBarLayout.as`: shared stage-to-bar geometry calculations.

If the UI needs to be rebuilt later, keep `ResearchProgressBarLobby.as` as the only WoT-facing root and keep pure construction, layout, and interaction logic in flat sibling helper classes like the list above.

- The exposed ActionScript callbacks used by the Python view wiring are:
  - `as_ping()`
  - `as_setContext(object)`
  - `as_setVisible(boolean)`