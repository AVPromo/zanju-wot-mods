"""Show which mods take each shared file of mods-common/, and stop on any fault.

    zwm shared            every shared module and script, with the mods that take it
    zwm shared <mod>...   the shared modules and scripts that each named mod takes

A mod takes a shared file by importing it, so this map comes from the imports in the mods and
in the shared files themselves. Nothing else declares it. See "Shared Modules" in
docs/reference/runtime-layout-and-packaging.md.
"""

from __future__ import annotations

import sys

from ..core import mods_common
from ..core.console import detail, section, success
from ..core.mod_cli import discover_mods


def _print_files(kind, mapping):
    section("Shared {}".format(kind))
    for name in sorted(mapping):
        mods = mapping[name]
        detail("{}: {}".format(name, ", ".join(mods) if mods else "no mod imports it"), verbose=True)


def _print_mods(mod_names):
    for mod_name in mod_names:
        section(mod_name)
        detail("modules: {}".format(", ".join(mods_common.modules_for(mod_name)) or "none"), verbose=True)
        detail("scripts: {}".format(", ".join(mods_common.scripts_for(mod_name)) or "none"), verbose=True)


def _main(argv):
    known = discover_mods()
    unknown = [name for name in argv if name not in known]
    if unknown:
        raise RuntimeError("Unknown mod: {}. Available mods: {}".format(", ".join(unknown), ", ".join(known)))
    mods_common.check()
    if argv:
        _print_mods(argv)
    else:
        mapping = mods_common.shared_map()
        _print_files("modules", mapping["modules"])
        _print_files("scripts", mapping["scripts"])
    success("Shared files are consistent")


def main():
    try:
        _main(sys.argv[1:])
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
