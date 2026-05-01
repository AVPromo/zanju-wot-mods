# World of Tanks Modding Knowledge Base

This repository contains a practical knowledge base and mod development workspace for World of Tanks, based on:

- Local installation analysis from `C:\Games\World_of_Tanks_EU` (current version seen: `2.2.1.1`)
- Public mod sources from `https://github.com/Kurzdor/wotmods-public/`
- Web references (KoreanRandom, WG fair-play pages)

## Repository Layout

```
mods/                          # one subdirectory per mod
  research-progress-bar/       # first mod
    meta.xml
    src/                       # Python source: top-level mod_*.py bootstrap + optional package
    res/                       # committed static assets and localisation only
    config/                    # committed default/user config source
    ui-src/                    # ActionScript source and generated UI build output
template/                      # scaffold — copy to mods/<new-mod> to start a mod
docs/                          # knowledge base
build.py                       # packages mods/ → dist/*.wotmod and dist/<release-bundle>/
dist/                          # gitignored release/export output
```

## Build

```powershell
python build.py                        # build all mods
python build.py research-progress-bar  # build one mod
```

Requires Python 3.6+ (tested on 3.14.4). No third-party packages needed.

Build outputs are split intentionally:

- Generated intermediate assets live under gitignored build directories such as `mods/<mod-name>/ui-src/build/`.
- Final user-facing export bundles live under gitignored `dist/`.
- Commit source files and default config sources; do not commit generated `.swf`, `.pyc`, or `.wotmod` artifacts.

## Dev Commands

Set `WOT_GAME_DIR` in `.env` first (example in `.env.example`).
Set `WOT_PYTHON2_EXE` as well; it is required in this repo's current stack so build output includes Python 2 `.pyc` scripts.

```powershell
# Build + deploy all mods (default)
python dev_test_deploy.py

# Remove deployed package + config for all mods
python dev_test_cleanup.py

# Preview cleanup targets without deleting
python dev_test_cleanup.py --dry-run

# Fast local iteration: cleanup + deploy
python dev_test_cycle.py

# Fast local iteration with clean python.log (no archive, opt-in)
python dev_test_cycle.py --fresh-log

# Target one mod only
python dev_test_cycle.py research-progress-bar
```

`dev_test_deploy.py`, `dev_test_cleanup.py`, and `dev_test_cycle.py` auto-target the newest numeric folder under `WOT_GAME_DIR/mods/`.

## Start Here

1. Read `docs/01-mod-architecture.md`
2. Read `docs/02-local-install-findings.md`
3. Follow `docs/03-dev-workflow.md`
4. Keep `docs/04-ecosystem-links.md` open while developing
5. Use `docs/05-debugging-and-compatibility.md` when something breaks

## Important

- Always re-check fair play policy before shipping a mod update.
- Treat external examples as patterns, not guaranteed up-to-date APIs.
- Test every patch cycle (especially micro-patches) before release.
- For this WoT stack, keep a thin top-level `mod_*.py` bootstrap under `src/`; package-only entrypoints were not auto-discovered.
- For multi-file mods, keep implementation in a unique package under `src/`, include `__init__.py`, avoid bootstrap/package name collisions, and prefer relative intra-package imports.
- Future work: automate publishing the `dist/` release bundle through GitHub Releases/CI. That workflow is intentionally not implemented yet.
- For research-progress-bar crash boundaries and safe probe settings, see `docs/05-debugging-and-compatibility.md` section 8.
