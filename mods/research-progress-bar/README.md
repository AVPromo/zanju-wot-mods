# Zanju's Research Progress Bar

Custom hangar progress bar for World of Tanks.

## Scope

The current mod surface includes:

- research progress toward the next unlock
- field modification progress
- Tier XI upgrade-tree progress
- elite progress modes with optional badge filtering
- optional in-game settings integration when supported APIs are installed

## Install And Use

If you already have a prepared release bundle, follow the general install path in [Installing Mods](../../docs/installing-mods.md).

Runtime config lives under:

- `mods/configs/research-progress-bar/config.json`
- `mods/configs/research-progress-bar/i18n/`

## Build From Source

Build only this mod:

```powershell
wot_mods_build research-progress-bar
```

Deploy it to a local WoT install:

```powershell
wot_mods_deploy research-progress-bar
```

Fast cleanup and redeploy loop:

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
- Runtime localisation loads from the config-side `i18n/` directory with English fallback.
- WoT must be restarted to pick up packaged Python/UI changes after deployment.
