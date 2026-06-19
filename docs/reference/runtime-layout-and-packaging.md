# Runtime Layout And Packaging

## Typical WoT Runtime Folders

Common runtime locations:

- `mods/<game-version>/`
- `mods/configs/`
- `res_mods/<game-version>/`
- `res_mods/configs/`

## Package Shape

A `.wotmod` commonly contains:

- `res/` — the only required element; everything below lives under it
- compiled Python scripts under `res/scripts/client/gui/mods/*.pyc`
- optional UI assets such as SWFs under `res/gui/flash/*.swf`
- optional localisation assets under `res/mods/<namespace>/text/*.yml`
- optional `meta.xml` manifest at the archive root (`<id>`, `<version>`, `<name>`, `<description>`)
- optional root `LICENSE.md`

## Repository Build Rules

In this repository:

- authored Python sources live under `mods/<mod-name>/src/`
- `wot_mods_build` compiles them into the runtime package shape
- authored `config.template.json` is staged into `mods/configs/<mod-name>/config.json`
- authored `i18n/*.yml` files are staged into both packaged text resources and deployable config folders
- `ui/compile_ui.py` is auto-run by `wot_mods_build` when present

## Entry Point Rule

For this WoT stack, keep a top-level `mod_*.py` bootstrap in `src/`.
Package-only entry points were not reliably auto-discovered.

## Import Safety Rule

Do not use the same module name for both:

- the top-level bootstrap file
- the internal package directory

That pattern can shadow the package in `sys.modules` and break imports.

## Release Output

Build results go to `dist/`.
That output is intended to be disposable build output rather than authored source.
