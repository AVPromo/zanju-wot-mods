# Development Workflow (From Zero to First Working Mod)

## 0. Prerequisites

- **Python 3.6+** required for the build script (`build.py`).
  Verified working on **Python 3.14.4** (current install on this machine).
  Download from https://python.org/downloads — tick "Add to PATH" during setup.
- No third-party packages needed; `build.py` uses standard library only.

## 1. Choose Mod Type First

Pick one:

- Pure config mod (lowest risk)
- UI-only tweak (flash/gameface assets)
- Python behavior mod (hooks, controllers, events)
- Hybrid mod (Python + UI + config)

Start with a small Python mod or config mod for first iteration.

## 2. Set Up Safe Test Loop

1. Keep clean backups of `mods/` and `res_mods/`.
2. Test in one dedicated game version folder (`mods/2.2.1.1`).
3. Deploy only your changed files each run.
4. Launch client, reproduce scenario, inspect `python.log`.
5. Repeat quickly.

## 3. Packaging Approach

For distributable builds, package as `.wotmod` with internal `res/...` layout.

At minimum:

- `meta.xml`
- compiled script(s) under `res/scripts/client/...`
- any assets under `res/gui/...` or `res/mods/<namespace>/...`

## 4. Config Strategy

- Put user-editable config under `mods/configs/<mod-name>/`.
- Version config schema (`configVersion`) and migrate old settings.
- Keep defaults safe if file missing/corrupt.

## 5. Compatibility Strategy

- Detect optional dependencies and degrade gracefully.
- Guard every hook with null checks and exception handling.
- Keep per-mode feature toggles (event modes often break assumptions).

## 6. Release Checklist

- Works on current patch version
- No fatal tracebacks in startup, hangar, battle, results, replay exit
- Handles missing dependencies
- Includes changelog and clear install path
- Includes rollback instructions

## 7. Recommended Learning Sequence

1. Inspect one existing `.wotmod` structure
2. Recreate tiny no-op logger mod
3. Add one safe hook + log marker
4. Add simple config read/write
5. Add optional UI element
6. Add version migration and release notes
