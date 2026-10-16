# mods-common

Runtime files that several mods share. Each file here is the one authored copy of its module. `zwm build` puts it into the package of every mod that `manifest.json` gives it to, so each `.wotmod` still carries its own copy.

- `*.py` are Python modules, under `modules` in the manifest. The build compiles each one into the internal package of each mod that takes it.
- `gameface/*.js` are Gameface scripts, under `gameface` in the manifest. The build copies each one into the one Gameface folder of each mod that takes it, beside the modules that import it.

The tests are in `tests/`. The Python tests import a module from the stand-in package `mods_common`, which exists only while `zwm test` runs. The JavaScript tests import a script from `../gameface/`.

Read [Shared Modules](../docs/reference/runtime-layout-and-packaging.md#shared-modules) before you add or change a file here.
