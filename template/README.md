# Mod Template

Starter template for a new WoT mod. It follows the current repository shape:
source is committed, generated build output stays out of git, and the final
release bundle is emitted under `dist/`.

## Directory Layout

```
template/
  meta.xml                                     # mod identity and version
  config/
    config.json                                # user-editable config source
  src/
    mod_modname.py                             # top-level WoT loader bootstrap
    yourname_modname/                          # unique internal package
      __init__.py                              # Python 2 package marker
      main.py                                  # real mod implementation
  res/
    mods/com.yourname.modname/text/
      en.yml                                   # localisation strings
build.py                                       # packages mods/ → dist/*.wotmod
```

Recommended next step for anything non-trivial:

- keep `src/mod_<name>.py` as a thin loader only
- move real implementation into a unique package under `src/<package>/`
- include `__init__.py` in that package for Python 2 recognition

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
| `yourname_modname` | unique internal package name, e.g. `zanju_myfirstmod` |
| `modname` (config folder) | your short mod folder name |

### 2. Update meta.xml

- Set `<id>`, `<name>`, `<version>`, `<wot_client_version>`, `<description>`.
- `<wot_client_version>` must match the current game version.

### 3. Write your mod logic

Edit `src/mod_modname.py`:

- `init()` runs at client startup. Register event hooks here.
- `fini()` runs at shutdown. Unsubscribe from anything registered in `init()`.
- Keep hook bodies wrapped in `try/except`.

### 4. Build

```powershell
python build.py <your-mod-name>
```

Build output:

- `dist/com.yourname.modname_<version>.wotmod`
- `dist/com.yourname.modname_<version>/`

The release bundle directory contains:

- `mods/<wot_client_version>/com.yourname.modname_<version>.wotmod`
- `mods/configs/<your-mod-name>/`
- `README.txt`

### 5. Deploy for testing

Fast local iteration:

```powershell
python dev_test_cycle.py <your-mod-name>
```

Manual deploy:

```powershell
Copy-Item dist\com.yourname.modname_<version>.wotmod "C:\Games\World_of_Tanks_EU\mods\<wot_client_version>\"
Copy-Item mods\<your-mod-name>\config\config.json "C:\Games\World_of_Tanks_EU\mods\configs\modname\"
```

Then launch the game and check `C:\Games\World_of_Tanks_EU\python.log` for your mod's log lines.

### 6. Release checklist

- [ ] `meta.xml` updated with final id, version, and current `wot_client_version`
- [ ] No placeholder ids remain (`com.yourname.modname`)
- [ ] `init()` and `fini()` tested without traceback
- [ ] Tested in hangar, battle start, battle end, and replay exit
- [ ] Config missing/corrupt handled gracefully
- [ ] Fair play policy checked: https://worldoftanks.com/en/content/guide/fair_play/prohibited_mods
- [ ] EULA checked for automation/behavior restrictions
- [ ] Changelog written with exact WoT version compatibility noted
- [ ] Rollback/uninstall instructions included in release notes

## Notes

- Author Python in `src/`; `build.py` compiles it to Python 2 `.pyc` inside the final `.wotmod`.
- Keep the top-level bootstrap filename prefixed with `mod_` so ScriptLoader PRO discovers it.
- Do not commit generated `.pyc`, `.swf`, or `.wotmod` files.
- Keep generated intermediate files in ignored build directories such as `ui-src/build/`.
- Keep final user-facing export bundles in ignored `dist/`.
- Config under `mods/configs/` is never bundled into the `.wotmod`; it ships separately and remains user-editable.
- Update `<wot_client_version>` in `meta.xml` every patch cycle, even if nothing else changed.
