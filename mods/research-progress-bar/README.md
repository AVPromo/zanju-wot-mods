# Zanju's Research Progress Bar

Custom hangar progress bar for World of Tanks.

## Scope

The current mod surface includes:

- research progress toward the next unlock
- Tier XI upgrade-tree progress
- field modification progress
- elite progress modes with optional badge filtering
- optional in-game settings integration when supported APIs are installed

## Install And Use

If you already have a prepared release bundle, follow the general install path in [Installing Mods](../../docs/installing-mods.md).

The standalone configurator release shape for this mod can include companion `.wotmod` packages for `ModsSettingsApi`, `ModsListApi`, and `net.openwg.gameface`. When that bundle is used, copy the whole included `mods/` tree together rather than only `zanju.researchprogressbar_*.wotmod`.

Runtime config lives under:

- `mods/configs/research-progress-bar/config.json`
- `mods/configs/research-progress-bar/i18n/`

Local remembered UI state is separate from the user-editable config. The mod now remembers the last selected progress mode per vehicle in an AppData-backed cache so reinstalls do not wipe that per-vehicle selection history.

Current cache path resolves to:

- `%APPDATA%\zanju_wot_mods_cache\research_progress_bar.json`

If `%APPDATA%` is unavailable, the runtime falls back to `%LOCALAPPDATA%`, then `%USERPROFILE%\AppData\Roaming`. The file uses named root sections so future cache types can be added without spreading unrelated values across the JSON root; the current per-vehicle remembered mode data lives under `modeSelection.vehicles`.

## Build From Source

Build the default standalone-configurator variant of this mod after fetching the pinned companion artifacts:

```powershell
wot_mods_fetch_companion_artifacts
wot_mods_build research-progress-bar
```

Build only the main mod package when you intentionally want to skip the companion `.wotmod` files:

```powershell
wot_mods_build --no-companion-bundle research-progress-bar
```

Deploy the default standalone-configurator variant to a local WoT install after fetching the pinned companion artifacts. Build first, and keep WoT closed while deploying:

```powershell
wot_mods_build research-progress-bar
wot_mods_fetch_companion_artifacts
wot_mods_deploy research-progress-bar
```

Deploy only the main mod package to a local WoT install:

```powershell
wot_mods_build --no-companion-bundle research-progress-bar
wot_mods_deploy --no-companion-bundle research-progress-bar
```

Fast cleanup, rebuild, and redeploy loop:

```powershell
wot_mods_cycle research-progress-bar
```

For the general build/toolchain workflow, see [Building From Source](../../docs/building-from-source.md).

## Develop

Important local paths:

- package metadata: `meta.xml`
- authored config source: `config.json`
- authored localisation: `i18n/`
- Python source: `src/`
- Scaleform UI source: `ui/`

The UI is compiled through `ui/compile_ui.py`, and `wot_mods_build` runs that compiler automatically before packaging.

For the wider repository workflow, see:

- [Developing Mods](../../docs/developing-mods.md)
- [Architecture](../../docs/architecture.md)
- [Technical Reference](../../docs/reference/README.md)

## Notes

- The mod is designed to keep working from config alone when optional ecosystem UI/settings APIs are missing.
- When the optional `ModsSettingsApi` stack is present, the in-game configurator exposes `enabled`, reminder toggles, `Research` with hypothetical tier XI / real-only / off options, `Upgrades`, `Field Mods`, and `Elite`, and writes changes back to `mods/configs/research-progress-bar/config.json`.
- The configurator template intentionally omits `settingsVersion` so template diffs remain eligible for refresh without version-gating.
- The standalone configurator bundle uses a tracked manifest plus ignored local cache for companion artifacts; update the pins with `wot_mods_update_companion_manifest`, then repopulate the cache with `wot_mods_fetch_companion_artifacts`.
- On the first visit to a vehicle, or when a remembered mode is no longer available, the bar falls back to the left-most available mode.
- The remembered per-vehicle mode cache is loaded once during startup, kept in memory during play, and written back with a small best-effort debounce instead of re-reading/writing on every vehicle switch.
- Runtime localisation loads from the config-side `i18n/` directory with English fallback.
- WoT must be restarted to pick up packaged Python/UI changes after deployment.

## UI Notes

- `scaleformPrototypeEnabled` controls whether the custom SWF path is active.
- The SWF-specific source split, compile entrypoint, and local UI build notes live in [Research Progress Bar UI](../../docs/reference/research-progress-bar-ui.md).
