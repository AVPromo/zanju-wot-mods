# Architecture

This page explains how mods in this repository are structured, packaged, and loaded by World of Tanks.

## Packaging Model

A distributable mod is usually a `.wotmod` archive containing:

- `meta.xml`
- compiled Python scripts under `res/scripts/client/gui/mods/`
- optional UI assets such as SWFs under `res/gui/flash/`
- optional localisation assets under `res/mods/<namespace>/text/`

## Repository Layout

A typical mod in this repo looks like this:

```text
mods/<mod-name>/
  meta.xml
  src/
    mod_<bootstrap>.py
    <internal_package>/
      __init__.py
      main.py
      ...
  config.json
  i18n/
  ui/
```

## Python Entry Points

In this client stack, the stable pattern is:

- keep a thin top-level `mod_*.py` bootstrap in `src/`
- place real implementation in a uniquely named internal package
- keep `__init__.py` in that package for Python 2 recognition
- prefer explicit relative imports inside the package

Do not rely on a package-only entry point.
Do not use the same name for the bootstrap file and the internal package.

## Runtime Locations

Common WoT runtime locations are:

- `mods/<game-version>/` for `.wotmod` packages
- `mods/configs/` for user-editable config
- `res_mods/<game-version>/` for override-style assets
- `res_mods/configs/` for some ecosystem tooling

## Build And Staging Rules

- `build.py` compiles Python sources into WoT-ready output.
- `build.py` also stages authored config and localisation files into runtime-shaped release output.
- Mods with UI sources can provide `ui/compile_ui.py`; `build.py` runs it automatically before packaging.
- Generated SWF output belongs in ignored build folders, not in source control.

## UI Pattern Used In This Repo

For custom lobby UI, the stable pattern is:

- compile ActionScript externally
- load the SWF through WoT view registration
- keep the SWF root on a WoT-compatible `IView` implementation such as `AbstractView`
- let WoT own the display tree attachment

For more detailed UI/runtime notes, see [UI And Scaleform](reference/ui-and-scaleform.md).

## Dependency Philosophy

Shared mod APIs should be optional unless the mod truly cannot run without them.
If a dependency is absent, the mod should degrade gracefully instead of crashing.

## Related Reading

- [Building From Source](building-from-source.md)
- [Developing Mods](developing-mods.md)
- [Technical Reference](reference/README.md)
