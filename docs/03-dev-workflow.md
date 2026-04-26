# Development Workflow (From Zero to First Working Mod)

## 0. Prerequisites

- **Python 3.6+** required for the build script (`build.py`).
  Verified working on **Python 3.14.4** (current install on this machine).
  Download from https://python.org/downloads — tick "Add to PATH" during setup.
- **Python 2.7** required for this repository's current WoT mod stack runtime compatibility.
  It is used to compile `src/*.py` to Python 2 `.pyc` that ScriptLoader PRO actually executes.
- No third-party packages needed; `build.py` uses standard library only.

## 0.1 Local Development Scripts

These scripts are meant for fast local iteration against your installed game client.

Before using them, configure `.env` in repo root:

- `WOT_GAME_DIR=C:\Games\World_of_Tanks_EU`
- `WOT_PYTHON2_EXE=C:\Python27\python.exe` (required in this repo's current stack)

Scripts:

- `python build.py`
  - Builds all mods under `mods/` into `dist/*.wotmod`.
  - `WOT_PYTHON2_EXE` is used to compile `src/*.py` to Python 2 `.pyc` before packaging.
  - Use `python build.py <mod-name>` to build one mod.
- `python dev_test_deploy.py`
  - Builds target mods, then deploys package + config to `WOT_GAME_DIR`.
  - Default target is all mods under `mods/`.
- `python dev_test_cleanup.py`
  - Removes deployed package + config for target mods from `WOT_GAME_DIR`.
  - Supports safe preview mode: `python dev_test_cleanup.py --dry-run`.
- `python dev_test_cycle.py`
  - Runs cleanup, then deploy (quick full refresh loop).
  - If WoT is running, package file replacement may be skipped as "in use".
  - Supports dry-run: `python dev_test_cycle.py --dry-run` (cleanup preview only).
  - Supports fresh log mode: `python dev_test_cycle.py --fresh-log` (truncates `python.log`, no archive).
  - `--fresh-log` requires WoT to be closed.

Recommended daily loop:

1. `python dev_test_cycle.py <mod-name>`
2. Launch WoT and load hangar/battle scenario
3. Check `C:\Games\World_of_Tanks_EU\python.log`
4. Repeat

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

### 5.1 Probe Escalation Rule (Post-Progression Data)

For any new field-mod/post-progression introspection, escalate in small steps and verify stability between each step:

1. completion-only
2. steps-only
3. state-only
4. next-step-only
5. full (only if all previous steps remain stable)

If a hard crash appears (no traceback, log stops mid-update), immediately roll back one probe level and re-test.

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
