# mods-common

Runtime files that several mods share. Each file here is the one authored copy of its module. A mod takes a file by importing it, and `zwm build` puts the file into the package of every mod that imports it, so each `.wotmod` still carries its own copy. `zwm shared` shows which mods take each file and each string.

- `*.py` are Python modules. The build compiles each one into the internal package of each mod that imports it, for example with `from .. import hangar_child`.
- `gameface/*.js` are Gameface scripts. The build copies each one into the one Gameface folder of each mod that imports it, beside the modules that import it, for example with `import { el } from './helpers.js'`.
- `i18n/*.yml` are strings that several mods use, in the layout of the `i18n/` folder of a mod. A mod takes a key when its code uses the key. The build adds the keys that a mod takes to the end of its language files. See [Translating](../docs/translating.md).

The files on 16 October 2026: the Python modules `card_window`, `hangar_child`, `localization`, `mod_menu`, `mode_gate`, `route_gate`, `storage` and `view_claim`, and the Gameface scripts `card_host`, `countdown`, `helpers`, `model_bridge` and `tray`. Each one starts with what it holds and why.

The tests are in `tests/`. The Python tests import a module from the stand-in package `mods_common`, which exists only while `zwm test` runs. The JavaScript tests import a script from `../gameface/`.

Read [Shared Modules](../docs/reference/runtime-layout-and-packaging.md#shared-modules) before you add or change a file here.
