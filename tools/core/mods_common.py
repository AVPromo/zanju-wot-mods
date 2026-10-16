"""The runtime files that several mods share, and which mods take each one.

Each shared file has one authored copy under mods-common/. A Python module is under
`modules` in mods-common/manifest.json: `zwm build` compiles it into the package of every mod
that takes it, the same way it adds `_mod_meta`. A Gameface script is under `gameface`: the
build copies mods-common/gameface/<name>.js into the one Gameface folder of every mod that takes
it, `res/gui/gameface/mods/<namespace>/`. Thus each .wotmod still carries its own copy and needs
no other mod. See "Shared Modules" in docs/reference/runtime-layout-and-packaging.md.
"""

from __future__ import annotations

import glob
import json
import os

from .mod_cli import discover_mods
from .paths import MODS_COMMON_DIR, MODS_COMMON_MANIFEST_PATH, MODS_DIR

MANIFEST_LABEL = "mods-common/manifest.json"
SCRIPTS_DIR = os.path.join(MODS_COMMON_DIR, "gameface")
GAMEFACE_MODS_REL = os.path.join("res", "gui", "gameface", "mods")


def _read_manifest_file():
    with open(MODS_COMMON_MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def read_manifest():
    """Return {module name: [mod name, ...]} from the manifest."""
    return _read_manifest_file()["modules"]


def read_scripts():
    """Return {Gameface script name: [mod name, ...]} from the manifest."""
    return _read_manifest_file().get("gameface", {})


def script_path(name):
    return os.path.join(SCRIPTS_DIR, "{}.js".format(name))


def scripts_for(mod_name, scripts=None):
    """Return the sorted names of the shared Gameface scripts that this mod takes."""
    scripts = read_scripts() if scripts is None else scripts
    return sorted(name for name, mods in scripts.items() if mod_name in mods)


def script_consumers_of(name, scripts=None):
    """Return the sorted names of the mods that take this shared Gameface script."""
    scripts = read_scripts() if scripts is None else scripts
    return sorted(scripts.get(name, ()))


def gameface_namespaces(mod_name):
    """Return the folders under res/gui/gameface/mods/ of this mod."""
    root = os.path.join(MODS_DIR, mod_name, GAMEFACE_MODS_REL)
    if not os.path.isdir(root):
        return []
    return sorted(name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name)))


def gameface_namespace(mod_name):
    """Return the one Gameface folder of this mod, or None when it has none or several."""
    namespaces = gameface_namespaces(mod_name)
    return namespaces[0] if len(namespaces) == 1 else None


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

    problems.extend(_find_script_problems(known_mods))
    return problems


def _find_script_problems(known_mods):
    """The same rules for the shared Gameface scripts as for the shared Python modules."""
    scripts = read_scripts()
    problems = []
    for name in sorted(scripts):
        if not os.path.isfile(script_path(name)):
            problems.append(
                "{} lists the script {}, but mods-common/gameface/{}.js does not exist.".format(
                    MANIFEST_LABEL, name, name
                )
            )
        for mod_name in sorted(scripts[name]):
            if mod_name not in known_mods:
                problems.append(
                    "{} gives the script {} to {}, but mods/{} does not exist.".format(
                        MANIFEST_LABEL, name, mod_name, mod_name
                    )
                )
            elif gameface_namespace(mod_name) is None:
                problems.append(
                    "{} gives the script {} to {}, but mods/{}/res/gui/gameface/mods/ does not hold "
                    "exactly one folder. The build copies the script into that one folder.".format(
                        MANIFEST_LABEL, name, mod_name, mod_name
                    )
                )

    for path in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.js"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name not in scripts:
            problems.append(
                "mods-common/gameface/{}.js is not in {}. Add it, or delete the file.".format(name, MANIFEST_LABEL)
            )

    for name in sorted(scripts):
        pattern = os.path.join(MODS_DIR, "*", GAMEFACE_MODS_REL, "*", "{}.js".format(name))
        for path in sorted(glob.glob(pattern)):
            rel_path = os.path.relpath(path, os.path.dirname(MODS_DIR)).replace(os.sep, "/")
            problems.append(
                "{} has the name of the shared script mods-common/gameface/{}.js, and the build puts "
                "that script at this path in each mod that takes it. Rename or delete this file.".format(
                    rel_path, name
                )
            )
    return problems


def check():
    """Stop with every fault that find_problems reports."""
    problems = find_problems()
    if problems:
        raise RuntimeError("Shared modules are not consistent:\n" + "\n".join("- " + p for p in problems))
