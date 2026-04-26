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
    src/                       # Python source (compiled to .pyc for release)
    res/                       # bundled assets and localisation
    config/                    # user config (shipped separately, not in .wotmod)
template/                      # scaffold — copy to mods/<new-mod> to start a mod
docs/                          # knowledge base
build.py                       # packages mods/ → dist/*.wotmod
dist/                          # build output (gitignored)
```

## Build

```powershell
python build.py                        # build all mods
python build.py research-progress-bar  # build one mod
```

Requires Python 3.6+ (tested on 3.14.4). No third-party packages needed.

## Dev Commands

Set `WOT_GAME_DIR` in `.env` first (example in `.env.example`).

```powershell
# Build + deploy all mods (default)
python dev_test_deploy.py

# Remove deployed package + config for all mods
python dev_test_cleanup.py

# Preview cleanup targets without deleting
python dev_test_cleanup.py --dry-run

# Fast local iteration: cleanup + deploy
python dev_test_cycle.py

# Target one mod only
python dev_test_cycle.py research-progress-bar
```

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
