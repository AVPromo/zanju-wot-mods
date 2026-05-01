# Development Workflow (From Zero to First Working Mod)

## 0. Prerequisites

- **Python 3.6+** required for the build script (`build.py`).
  Verified working on **Python 3.14.4** (current install on this machine).
  Download from https://python.org/downloads — tick "Add to PATH" during setup.
- **Python 2.7** required for this repository's current WoT mod stack runtime compatibility.
  It is used to compile `src/**/*.py` to Python 2 `.pyc` that ScriptLoader PRO actually executes.
- No third-party Python packages needed; `build.py` uses standard library only.
- **Java** is required for SWF/UI development with the free ActionScript toolchain.
- **Apache Flex SDK** is required when building `.swf` UI assets from ActionScript sources (`mxmlc`).
- **FFDec** is required for inspecting existing WoT/mod `.swf` files and reverse-engineering view structure.

Current machine status:

- `java -help` works
- `mxmlc -help` works
- `ffdec-cli.exe -help` works
- `JAVA_HOME`, `ANT_HOME`, and `FLEX_HOME` are present in the environment

## 0.1 UI Tooling Paths

For garage/battle UI work there are two practical paths:

- **Code-first free path**: Java + Apache Flex SDK + FFDec + a text editor.
- **Visual authoring path**: Adobe Animate/Flash Professional (optional, paid).

Current repo direction:

- Prefer the free code-first ActionScript 3 path for new UI work.
- Use FFDec to inspect existing WoT or third-party SWFs.
- Keep authored SWFs under `mods/<mod-name>/res/gui/flash/` so `build.py` can package them unchanged.
- Keep Python/AS3 integration logic in `mods/<mod-name>/src/`.
- For garage widgets that should behave like real WoT lobby UI, prefer a custom Scaleform window over `GUIFlash`.
- A custom lobby `.swf` loaded through `ViewSettings(..., WindowLayer.WINDOW, ...)` must use a WoT `IView`-compatible AS3 root such as `net.wg.infrastructure.base.AbstractView`; a plain `Sprite` root is rejected by the loader.
- Cross-check against the installed working mod `tv.lebwa.gunmarks_1.3.07.wotmod`: WoT loads `GunMarksLebwaLobby` as an `SFWindow`, the SWF root extends `AbstractView`, and that root injects a draggable panel MovieClip into the lobby/hangar display tree.
- For local compilation without bundled WG source/SWCs, a tiny external compile-time stub SWC is sufficient for `mxmlc`; WoT still provides the real runtime implementation.

## 0.2 Local Development Scripts

These scripts are meant for fast local iteration against your installed game client.

Before using them, configure `.env` in repo root:

- `WOT_GAME_DIR=C:\Games\World_of_Tanks_EU`
- `WOT_PYTHON2_EXE=C:\Python27\python.exe` (required in this repo's current stack)

Scripts:

- `python build.py`
  - Builds all mods under `mods/` into `dist/*.wotmod`.
  - `WOT_PYTHON2_EXE` is used to compile `src/**/*.py` to Python 2 `.pyc` before packaging.
  - Any files placed under `mods/<mod-name>/res/` are copied into the archive as-is, including `.swf` assets.
  - Use `python build.py <mod-name>` to build one mod.
- `python dev_test_deploy.py`
  - Builds target mods, then deploys package + config to `WOT_GAME_DIR`.
  - Auto-detects the newest numeric folder under `WOT_GAME_DIR/mods/` and deploys there.
  - Default target is all mods under `mods/`.
- `python dev_test_cleanup.py`
  - Removes deployed package + config for target mods from `WOT_GAME_DIR`.
  - Auto-detects the newest numeric folder under `WOT_GAME_DIR/mods/` before removing deployed packages.
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

For UI work, extend the loop:

1. Build or update the `.swf` with `mxmlc`
2. Place the generated `.swf` under `mods/<mod-name>/res/gui/flash/`
3. Run `python dev_test_cycle.py <mod-name>`
4. Launch WoT, open the target screen, inspect `python.log`
5. Repeat

## 1. Choose Mod Type First

Pick one:

- Pure config mod (lowest risk)
- UI-only tweak (flash/gameface assets)
- Python behavior mod (hooks, controllers, events)
- Hybrid mod (Python + UI + config)

Start with a small Python mod or config mod for first iteration.
For custom draggable garage widgets, treat the work as a hybrid mod even if the first prototype is UI-heavy.

## 2. Set Up Safe Test Loop

1. Keep clean backups of `mods/` and `res_mods/`.
2. Test against the newest installed game version folder under `mods/`.
3. Deploy only your changed files each run.
4. Launch client, reproduce scenario, inspect `python.log`.
5. Repeat quickly.

## 3. Packaging Approach

For distributable builds, package as `.wotmod` with internal `res/...` layout.

At minimum:

- `meta.xml`
- a compiled top-level `mod_*.pyc` bootstrap under `res/scripts/client/gui/mods/`
- optional package modules under `res/scripts/client/gui/mods/<package>/...`
- any assets under `res/gui/...` or `res/mods/<namespace>/...`

Safe Python shape for this repo:

- keep a thin loader at `mods/<mod-name>/src/mod_<name>.py`
- move real logic into a unique package under `mods/<mod-name>/src/<package>/`
- include `__init__.py` in that package for Python 2 recognition
- use explicit relative imports inside the package when importing sibling modules
- do not expect a package-only entrypoint to auto-load, and do not use the same name for the bootstrap file and the package directory

For ActionScript-based UI mods:

- author `.as` source outside the packaged `res/` tree if desired
- compile to `.swf` with `mxmlc`
- ship only the resulting `.swf` under `res/gui/flash/`
- keep raw source/assets in the repo, not inside the game install

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

Before escalating into deeper runtime step probes, check whether the same value is already materialized by an existing UI presenter/view-model path.

- For Tier XI skill trees in WoT 2.2.1.1, the Vehicle Hub upgrades UI can safely materialize node prices through the presenter/model layer.
- That path is still UI-scoped: if the player has not opened the relevant upgrades UI in the current session, the garage-side code does not have those real prices yet.
- Treat presenter-derived values as a safe validation/opportunistic cache path, not as proof that the underlying step method is safe to call from scheduled hangar updates.

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
5. Inspect a working UI `.swf` in FFDec and note view names, symbols, and data flow
6. Build one minimal ActionScript 3 `.swf` with `mxmlc`
7. Load one optional UI element in WoT
8. Add version migration and release notes

## 8. Research Progress Bar UI Baseline

For the current research-progress-bar direction, the stable baseline is:

1. Use `compile_ui.py` as the canonical SWF compiler. `build.py research-progress-bar` and `dev_test_cycle.py research-progress-bar` run it automatically before packaging, so manual UI builds are only needed for SWF-only iteration.
2. Keep the SWF root on a WoT `IView`-compatible class such as `AbstractView`.
3. Load the bar as an `SFWindow` and let WoT attach it to the main window automatically.
4. Keep that window persistent and toggle SWF visibility for hide/show cases instead of destroying and reloading it for transient popups.
5. Treat only the default hangar route as visible. Use both container hooks and lobby-route tracking because `hangar/loadout/*` screens do not always emit a separate container view.
6. Use correct z-order for ordinary popup windows like chat, contacts, session statistics, and lobby menu rather than hiding the bar.
7. Keep structured `python.log` lines during visibility tuning; remove or reduce them only after the behavior is stable.
