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
