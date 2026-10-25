"""The runtime files that several mods share, and which mods take each one.

Each shared file has one authored copy under mods-common/: a Python module as
mods-common/<name>.py, a Gameface script as mods-common/gameface/<name>.js. `zwm build` compiles a
shared module into the package of every mod that takes it, the same way it adds `_mod_meta`, and
copies a shared script into the one Gameface folder of every mod that takes it,
`res/gui/gameface/mods/<namespace>/`. Thus each .wotmod still carries its own copy and needs no
other mod.

A mod takes a shared file by importing it. Nothing else declares it:

- Python: a relative import that reaches the root of the mod's package and names a shared
  module, such as `from .. import hangar_child` in a subpackage or `from .localization import
  get_text` at the root, anywhere in mods/<mod>/src/. An absolute import through the package
  name counts too.
- Gameface: `import ... from './<name>.js'`, or `import './<name>.js'`, in a script of the mod's
  Gameface folder.

Shared files import each other too, `countdown.js` imports `helpers.js` for one, so the set of a
mod is closed over those imports. Only these static forms count: a shared module that is loaded
by `__import__` with a string, or a dynamic `import()`, is not found and does not ship.

See "Shared Modules" in docs/reference/runtime-layout-and-packaging.md.
"""

from __future__ import annotations

import ast
import functools
import glob
import os
import re

from .mod_cli import discover_mods
from .paths import MODS_COMMON_DIR, MODS_DIR

SCRIPTS_DIR = os.path.join(MODS_COMMON_DIR, "gameface")
GAMEFACE_MODS_REL = os.path.join("res", "gui", "gameface", "mods")
# The build adds this module to every package, so a shared module may import it.
BUILD_META_MODULE = "_mod_meta"

# One import of a script beside the importing one. Comments are removed before the match.
_JS_IMPORT = re.compile(r"""\b(?:import|from)\s*['"]\./([A-Za-z0-9_\-]+)\.js['"]""")
_JS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_JS_LINE_COMMENT = re.compile(r"(^|[^:])//[^\n]*")


def module_path(name):
    return os.path.join(MODS_COMMON_DIR, "{}.py".format(name))


def script_path(name):
    return os.path.join(SCRIPTS_DIR, "{}.js".format(name))


def module_names():
    """Return the sorted names of the shared Python modules."""
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(MODS_COMMON_DIR, "*.py")))


def script_names():
    """Return the sorted names of the shared Gameface scripts."""
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(SCRIPTS_DIR, "*.js")))


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


def _package_names(mod_name):
    src = os.path.join(MODS_DIR, mod_name, "src")
    if not os.path.isdir(src):
        return []
    return sorted(
        name for name in os.listdir(src) if os.path.isfile(os.path.join(src, name, "__init__.py"))
    )


def python_imports(source, rel_parts, own_packages=(), filename="<source>"):
    """Return the names that one Python file imports from the root of its package.

    `rel_parts` are the folders from the package root to the file, empty for a file at the root.
    `own_packages` are the names of the package, for an absolute import through it.
    """
    tree = ast.parse(source, filename=filename)
    found = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.ImportFrom):
            module_parts = node.module.split(".") if node.module else []
            if node.level:
                up = node.level - 1
                if up > len(rel_parts) or len(rel_parts) - up:
                    # Beyond the package, or into a subpackage rather than the root.
                    continue
                targets = module_parts[:1] or [alias.name for alias in node.names]
            elif module_parts and module_parts[0] in own_packages:
                targets = module_parts[1:2] or [alias.name for alias in node.names]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] in own_packages and len(parts) > 1:
                    targets.append(parts[1])
        found.update(targets)
    return found


def script_imports(source):
    """Return the names of the scripts beside it that one Gameface script imports."""
    source = _JS_BLOCK_COMMENT.sub("", source)
    source = _JS_LINE_COMMENT.sub(lambda match: match.group(1), source)
    return set(_JS_IMPORT.findall(source))


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


@functools.lru_cache(maxsize=None)
def _shared_graph():
    """({module: imported shared modules}, {script: imported shared scripts}, problems)."""
    modules = set(module_names())
    scripts = set(script_names())
    problems = []
    module_graph = {}
    for name in sorted(modules):
        try:
            imported = python_imports(_read(module_path(name)), (), filename=module_path(name))
        except SyntaxError as exc:
            problems.append("mods-common/{}.py does not parse: {}".format(name, exc))
            imported = set()
        unknown = sorted(imported - modules - {BUILD_META_MODULE})
        if unknown:
            problems.append(
                "mods-common/{}.py imports {} from the package root, and no shared module has that name.".format(
                    name, ", ".join(unknown)
                )
            )
        module_graph[name] = imported & modules
    script_graph = {}
    for name in sorted(scripts):
        imported = script_imports(_read(script_path(name)))
        unknown = sorted(imported - scripts)
        if unknown:
            problems.append(
                "mods-common/gameface/{}.js imports {}, and no shared script has that name.".format(
                    name, ", ".join("./{}.js".format(item) for item in unknown)
                )
            )
        script_graph[name] = imported & scripts
    return module_graph, script_graph, tuple(problems)


def _closure(names, graph):
    seen = set(names)
    pending = list(names)
    while pending:
        for dependency in graph.get(pending.pop(), ()):
            if dependency not in seen:
                seen.add(dependency)
                pending.append(dependency)
    return seen


@functools.lru_cache(maxsize=None)
def _mod_imports(mod_name):
    """(shared modules, shared scripts, problems) that this mod takes, with what those import."""
    module_graph, script_graph, _ = _shared_graph()
    problems = []
    modules = set()
    src = os.path.join(MODS_DIR, mod_name, "src")
    for package in _package_names(mod_name):
        package_dir = os.path.join(src, package)
        for path in sorted(glob.glob(os.path.join(package_dir, "**", "*.py"), recursive=True)):
            rel_dir = os.path.relpath(os.path.dirname(path), package_dir)
            rel_parts = () if rel_dir == "." else tuple(rel_dir.split(os.sep))
            try:
                imported = python_imports(_read(path), rel_parts, _package_names(mod_name), filename=path)
            except SyntaxError as exc:
                problems.append("{} does not parse, so its shared imports are unknown: {}".format(path, exc))
                continue
            modules.update(imported & set(module_graph))
    scripts = set()
    root = os.path.join(MODS_DIR, mod_name, GAMEFACE_MODS_REL)
    for path in sorted(glob.glob(os.path.join(root, "**", "*.js"), recursive=True)):
        scripts.update(script_imports(_read(path)) & set(script_graph))
    return (
        tuple(sorted(_closure(modules, module_graph))),
        tuple(sorted(_closure(scripts, script_graph))),
        tuple(problems),
    )


def modules_for(mod_name):
    """Return the sorted names of the shared modules that this mod takes."""
    return list(_mod_imports(mod_name)[0])


def scripts_for(mod_name):
    """Return the sorted names of the shared Gameface scripts that this mod takes."""
    return list(_mod_imports(mod_name)[1])


def consumers_of(name):
    """Return the sorted names of the mods that take this shared module."""
    return [mod_name for mod_name in discover_mods() if name in modules_for(mod_name)]


def script_consumers_of(name):
    """Return the sorted names of the mods that take this shared Gameface script."""
    return [mod_name for mod_name in discover_mods() if name in scripts_for(mod_name)]


def shared_map():
    """Return {"modules": {name: [mod, ...]}, "scripts": {name: [mod, ...]}} for every shared file."""
    return {
        "modules": {name: consumers_of(name) for name in module_names()},
        "scripts": {name: script_consumers_of(name) for name in script_names()},
    }


def find_problems():
    """Return one message for each fault in the shared files or in the mods.

    The name checks cover every mod, not only the mods that take a file. A file with a shared
    file's name in some other mod is either a copy that went its own way, or a different file that
    would be taken for the shared one.
    """
    problems = list(_shared_graph()[2])
    for mod_name in discover_mods():
        problems.extend(_mod_imports(mod_name)[2])

    for name in module_names():
        for path in sorted(glob.glob(os.path.join(MODS_DIR, "*", "src", "*", "{}.py".format(name)))):
            rel_path = os.path.relpath(path, os.path.dirname(MODS_DIR)).replace(os.sep, "/")
            problems.append(
                "{} has the name of the shared module mods-common/{}.py, and the build puts that module "
                "at this path in each mod that imports it. Rename this file. If it is a copy of the shared "
                "module, delete it: the mod takes the shared one by importing it.".format(rel_path, name)
            )

    for name in script_names():
        pattern = os.path.join(MODS_DIR, "*", GAMEFACE_MODS_REL, "*", "{}.js".format(name))
        for path in sorted(glob.glob(pattern)):
            rel_path = os.path.relpath(path, os.path.dirname(MODS_DIR)).replace(os.sep, "/")
            problems.append(
                "{} has the name of the shared script mods-common/gameface/{}.js, and the build puts that "
                "script at this path in each mod that imports it. Rename or delete this file.".format(rel_path, name)
            )

    for mod_name in discover_mods():
        if scripts_for(mod_name) and gameface_namespace(mod_name) is None:
            problems.append(
                "{} imports the shared scripts {}, but mods/{}/res/gui/gameface/mods/ does not hold exactly one "
                "folder. The build copies each script into that one folder.".format(
                    mod_name, ", ".join(scripts_for(mod_name)), mod_name
                )
            )
    return problems


def check():
    """Stop with every fault that find_problems reports."""
    problems = find_problems()
    if problems:
        raise RuntimeError("Shared modules are not consistent:\n" + "\n".join("- " + p for p in problems))
