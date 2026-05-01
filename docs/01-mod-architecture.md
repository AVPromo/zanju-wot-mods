# WoT Mod Architecture (Practical)

## 1. Main Packaging Model

In modern WoT modding, a mod is usually distributed as a `.wotmod` archive.
A `.wotmod` is a zip-like package that commonly contains:

- `meta.xml`
- `res/scripts/client/gui/mods/*.pyc` (compiled Python logic)
- Optional UI assets (for example `.swf` files)
- Optional localization and resource folders

From local inspection (`me.kurzdor.battleequipment_3.4.12.wotmod`):

- `res/scripts/client/gui/mods/mod_battleequipment.pyc`
- `res/gui/flash/battleEquipment.swf`
- `res/mods/me.kurzdor.battleequipment/text/*.yml`

### Required Python File Shape In This Repo

For authored source in this repository, the safe working shape is:

```text
mods/<mod-name>/
	src/
		mod_<bootstrap>.py
		<unique_package>/
			__init__.py
			main.py
			constants.py
	res/
	config/
```

What live WoT testing established:

- Author Python under `src/`; `build.py` compiles `src/**/*.py` into matching paths under `res/scripts/client/gui/mods/` inside the `.wotmod`.
- Keep a thin top-level bootstrap module whose filename starts with `mod_` if you want ScriptLoader PRO to auto-discover the mod.
- Do not rely on a package directory by itself as the entrypoint; package-only entrypoints were not auto-discovered in this client stack.
- Put the real implementation in a uniquely named internal package to avoid collisions in WoT's shared `gui/mods` import namespace.
- In Python 2, package directories need `__init__.py`.
- Do not give the bootstrap file and the package directory the same module name, or the loaded bootstrap module will shadow the package in `sys.modules`.
- Prefer explicit relative imports inside the package, such as `from .constants import ...`, instead of relying on absolute intra-package imports.

## 2. Runtime Locations

Common runtime folders:

- `mods/<game_version>/` for packaged mods (`.wotmod`)
- `mods/configs/` for user-editable JSON/YAML config
- `res_mods/<game_version>/` for resource/script overrides
- `res_mods/configs/` for some ecosystem tools and configs

In your install (`2.2.1.1`):

- `C:\Games\World_of_Tanks_EU\mods\2.2.1.1`
- `C:\Games\World_of_Tanks_EU\mods\configs`
- `C:\Games\World_of_Tanks_EU\res_mods\2.2.1.1`
- `C:\Games\World_of_Tanks_EU\res_mods\configs`

## 3. Typical Mod Stack Dependencies

Patterns seen across active mods and public repos:

- `ModsList API` for listing/integration in in-game mod UI
- `ModsSettingsAPI` for in-game settings pages
- `GUIFlash` or custom UI glue for scaleform/gameface widgets
- XVM/XFW integration for macro/config-driven workflows (optional)

Verified garage-window pattern from the installed working reference mod:

- `tv.lebwa.gunmarks_1.3.07.wotmod` loads `GunMarksLebwaLobby` as an `SFWindow` in the lobby.
- Its lobby SWF root extends `net.wg.infrastructure.base.AbstractView`, not plain `Sprite`.
- The root view creates and injects a draggable panel MovieClip into the real `LobbyPage`/`Hangar` display tree.
- This is the preferred reference pattern for custom draggable garage widgets in this repo.

Current repo baseline for the research-progress-bar garage UI:

- `ResearchProgressBarLobby` is loaded as a persistent `SFWindow` at `WindowLayer.WINDOW`.
- Let WoT attach that window to the main window automatically; the explicit-parent load path was not needed.
- Keep the window alive and toggle SWF visibility for transient hide/show cases. Destroying and reloading the window during ordinary popups caused flashing and could close focus-sensitive game UI.
- Use container-layer signals for real `SUB_VIEW` / `TOP_SUB_VIEW` changes, but also track the lobby route for hangar-local overlays.
- `hangar/loadout/*` screens can stay inside the hangar flow and only announce themselves through lobby-state-machine route changes.
- Ordinary `WINDOW` / `TOP_WINDOW` popups like chat, contacts, session statistics, and lobby menu should rely on correct z-order instead of forcing the bar to hide.

Authoring and inspection tools used in this repo:

- `Python 2.7` to produce WoT-compatible `.pyc`
- `Python 3.x` to run repo build/deploy scripts
- `Java` + `Apache Flex SDK` (`mxmlc`) for free code-first ActionScript 3 `.swf` authoring
- `FFDec` for `.swf` inspection and reverse-engineering

Important distinction:

- WoT provides the runtime that loads `.swf` UI assets.
- Our local toolchain is only for authoring, compiling, packaging, and inspection.
- A minimal external stub SWC can be used locally for compile-time typing against WoT base classes such as `AbstractView`; the real implementation still comes from WoT at runtime.

## 4. Patch-Resilience Patterns

From changelogs and ecosystem behavior:

- Keep battle-type allow/deny lists explicit and update them often.
- Add defensive checks for missing game objects and descriptors.
- Expect frequent API and path churn around events and seasonal modes.
- Move configs to stable paths and support migration logic between versions.

## 5. What Usually Breaks

- Hook targets renamed by patch
- Battle mode enums/types changed
- UI resources moved/removed
- Missing dependency mod (mod should fail gracefully)
- Config schema changes without migration
