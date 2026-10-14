# mods-common

Runtime modules that several mods share. Each file here is the one authored copy of its module. `zwm build` compiles it into the package of every mod that `manifest.json` gives it to, so each `.wotmod` still carries its own copy.

The tests for these modules are in `tests/`. They import a module from the stand-in package `mods_common`, which exists only while `zwm test` runs.

Read [Shared Modules](../docs/reference/runtime-layout-and-packaging.md#shared-modules) before you add or change a module here.
