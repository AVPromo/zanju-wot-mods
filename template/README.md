# Mod Template

Starter template for a new WoT mod. Contains a minimal working layout that
compiles into a distributable `.wotmod` package.

## Directory Layout

```
template/
  meta.xml                                     # mod identity and version
  config/
    config.json                                # user-editable config (ships separately)
  res/
    scripts/client/gui/mods/
      mod_modname.py                           # Python entry point
    mods/com.yourname.modname/text/
      en.yml                                   # localisation strings
build.py                                       # packages template/ → dist/*.wotmod
```

## Quick Start

### 0. Copy template to mods/

All real mods live under `mods/`. Copy this template there first:

```powershell
Copy-Item -Recurse template mods\<your-mod-name>
```

Then work entirely inside `mods/<your-mod-name>/`.

### 1. Rename things

Search-replace `modname` and `yourname` across all files:

| Placeholder | Replace with |
|---|---|
| `com.yourname.modname` | your reverse-domain mod id, e.g. `com.zanju.myfirstmod` |
| `mod_modname.py` | `mod_<yourmodname>.py` |
| `modname` (config folder) | your short mod folder name |

### 2. Update meta.xml

- Set `<id>`, `<name>`, `<version>`, `<wot_client_version>`, `<description>`.
- `<wot_client_version>` must match the current game version (e.g. `2.2.1.1`).

### 3. Write your mod logic

Edit `res/scripts/client/gui/mods/mod_modname.py`:

- `init()` — runs at client startup. Register event hooks here.
- `fini()` — runs at shutdown. Unsubscribe from any events registered in `init()`.
- Keep all hook bodies wrapped in `try/except`.

### 4. Build

```powershell
python build.py
```

Output: `dist/com.yourname.modname_<version>.wotmod`

### 5. Deploy for testing

```powershell
# Copy .wotmod into the game mod folder
Copy-Item dist\*.wotmod "C:\Games\World_of_Tanks_EU\mods\2.2.1.1\"

# Copy config (first run or after schema change)
Copy-Item template\config\config.json "C:\Games\World_of_Tanks_EU\mods\configs\modname\"
```

Then launch the game and check `C:\Games\World_of_Tanks_EU\python.log` for your mod's log lines.

### 6. Release checklist

- [ ] `meta.xml` updated with final id, version, and current `wot_client_version`
- [ ] No placeholder ids remain (`com.yourname.modname`)
- [ ] `init()` and `fini()` tested without traceback
- [ ] Tested in hangar, battle start, battle end, and replay exit
- [ ] Config missing/corrupt handled gracefully (falls back to defaults)
- [ ] Fair play policy checked: https://worldoftanks.com/en/content/guide/fair_play/prohibited_mods
- [ ] EULA checked for automation/behavior restrictions
- [ ] Changelog written with exact WoT version compatibility noted
- [ ] Rollback/uninstall instructions included in release notes

## Notes

- Python source (`.py`) files are loaded from `res_mods/` during development.
  Ship compiled `.pyc` files in the final `.wotmod` for release.
- Config under `mods/configs/` is never bundled into the `.wotmod`.
  It ships as a separate download and is user-editable.
- Update `<wot_client_version>` in `meta.xml` every patch cycle, even if nothing else changed.
