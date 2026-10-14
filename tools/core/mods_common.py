"""The runtime modules that several mods share, and which mods take each one.

Each shared module has one authored copy under mods-common/. `zwm build` compiles that copy into
the package of every mod that takes it, the same way it adds `_mod_meta`. Thus each .wotmod
still carries its own copy and needs no other mod. mods-common/manifest.json says which mods
take which module. See "Shared Modules" in docs/reference/runtime-layout-and-packaging.md.
"""

from __future__ import annotations

import glob
import json
import os

from .mod_cli import discover_mods
from .paths import MODS_COMMON_DIR, MODS_COMMON_MANIFEST_PATH, MODS_DIR

MANIFEST_LABEL = "mods-common/manifest.json"


def read_manifest():
    """Return {module name: [mod name, ...]} from the manifest."""
    with open(MODS_COMMON_MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)["modules"]


def module_path(name):
    return os.path.join(MODS_COMMON_DIR, "{}.py".format(name))


def modules_for(mod_name, manifest=None):
    """Return the sorted names of the shared modules that this mod takes."""
    manifest = read_manifest() if manifest is None else manifest
    return sorted(name for name, mods in manifest.items() if mod_name in mods)


def consumers_of(name, manifest=None):
    """Return the sorted names of the mods that take this shared module."""
    manifest = read_manifest() if manifest is None else manifest
    return sorted(manifest.get(name, ()))


def find_problems(manifest=None):
    """Return one message for each fault in the manifest or in the mods it names.

    The name check covers every mod, not only the mods that take a module. A file with a
    shared module's name in some other mod is either a copy that went its own way, or a
    different module that the next mod to take the shared one would overwrite.
    """
    manifest = read_manifest() if manifest is None else manifest
    known_mods = set(discover_mods())
    problems = []

    for name in sorted(manifest):
        if not os.path.isfile(module_path(name)):
            problems.append("{} lists {}, but mods-common/{}.py does not exist.".format(MANIFEST_LABEL, name, name))
        for mod_name in sorted(manifest[name]):
            if mod_name not in known_mods:
                problems.append(
                    "{} gives {} to {}, but mods/{} does not exist.".format(MANIFEST_LABEL, name, mod_name, mod_name)
                )

    for path in sorted(glob.glob(os.path.join(MODS_COMMON_DIR, "*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name not in manifest:
            problems.append("mods-common/{}.py is not in {}. Add it, or delete the file.".format(name, MANIFEST_LABEL))

    for name in sorted(manifest):
        for path in sorted(glob.glob(os.path.join(MODS_DIR, "*", "src", "*", "{}.py".format(name)))):
            rel_path = os.path.relpath(path, os.path.dirname(MODS_DIR)).replace(os.sep, "/")
            mod_name = rel_path.split("/")[1]
            if mod_name in manifest[name]:
                problems.append(
                    "{} has the name of the shared module mods-common/{}.py, and the build puts that "
                    "module at this path. Delete this file.".format(rel_path, name)
                )
            else:
                problems.append(
                    "{} has the name of the shared module mods-common/{}.py. Rename this file. "
                    "If it is a copy of the shared module, delete it and add {} to {}.".format(
                        rel_path, name, mod_name, MANIFEST_LABEL
                    )
                )

    return problems


def check():
    """Stop with every fault that find_problems reports."""
    problems = find_problems()
    if problems:
        raise RuntimeError("Shared modules are not consistent:\n" + "\n".join("- " + p for p in problems))
