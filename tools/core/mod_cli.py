"""Shared CLI plumbing for the mod-targeting zwm subcommands.

build / deploy / cleanup / cycle all parse the same `[--flags] [mod names...]`
shape, resolve `--all` vs explicit targets the same way, and wrap their entry
point in the same RuntimeError->SystemExit guard. These helpers are the single
source of that behaviour.

A mod can be named by its folder name or by its release acronym, in any case:
`zwm cycle crt pt --fresh-log` is `zwm cycle crucible-tracker premium-time --fresh-log`.
"""

from __future__ import annotations

import functools
import importlib.util
import os

from .console import success, warning
from .env import load_env
from .paths import MODS_DIR, REPO_ROOT

# The release scripts own the acronyms: derived from the name in meta.xml, or set in
# .github/scripts/release_acronyms.json. Reading them from there keeps `zwm cycle crt` and the
# tag `CRT@1.0.0` pointing at the same mod.
_RELEASE_LIB_PATH = os.path.join(REPO_ROOT, ".github", "scripts", "release_lib.py")


def discover_mods():
    """Return the sorted names of every mod directory under mods/."""
    if not os.path.isdir(MODS_DIR):
        return []
    return sorted(d for d in os.listdir(MODS_DIR) if os.path.isdir(os.path.join(MODS_DIR, d)))


@functools.lru_cache(maxsize=None)
def mod_acronyms():
    """Return {mod folder name: release acronym}, or {} when the release scripts cannot say."""
    try:
        spec = importlib.util.spec_from_file_location("zwm_release_lib", _RELEASE_LIB_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return {mod["mod_name"]: mod["acronym"] for mod in module.iter_mods()}
    except Exception:
        # A broken acronym list must not stop a build. The release check reports it.
        return {}


def resolve_mod_names(tokens):
    """Return the mod folder names for these tokens, in order and without repeats.

    A token is a folder name, or a release acronym in any case. A token that is neither is
    passed on as it is, so the caller reports it as a missing mod.
    """
    folders = set(discover_mods())
    by_acronym = {acronym.lower(): mod_name for mod_name, acronym in mod_acronyms().items()}
    names = []
    for token in tokens:
        name = token if token in folders else by_acronym.get(token.lower(), token)
        if name not in names:
            names.append(name)
    return names


class UsageError(Exception):
    """A command was invoked with arguments it cannot make sense of.

    Separate from RuntimeError, which reports a task that failed: this one says the request
    was never valid, so the caller prints the command's usage rather than a failure message.
    """


def split_targeting_args(argv, bool_flags):
    """Split argv into (flags, positionals) for a simple boolean-flag CLI.

    bool_flags maps each recognised `--flag` to the result key it sets True. Bare tokens are
    mod names; anything else that starts with `-` raises UsageError.

    That last rule matters more than it looks. These commands take mod names positionally, so
    a mistyped flag used to be accepted as a mod name and surfaced several steps later as
    "mod directory not found: --fresh-logfile" -- or, from `cycle`, as a subprocess traceback
    from the sub-command that inherited it. Rejecting it here names the actual mistake.
    """
    flags = dict.fromkeys(bool_flags.values(), False)
    positionals = []
    for arg in argv:
        key = bool_flags.get(arg)
        if key is not None:
            flags[key] = True
        elif arg.startswith("-"):
            raise UsageError("unknown option: {}".format(arg))
        else:
            positionals.append(arg)
    return flags, positionals


def parse_companion_targeting_args(argv):
    """Parse the shared build/deploy argv: companion-bundle flags + targets.

    Returns (include_companion_bundle, run_all, verbose, targets) where
    include_companion_bundle is True/False when forced by a flag, else None.
    """
    include_companion_bundle = None
    run_all = False
    verbose = False
    targets = []
    for arg in argv:
        if arg == "--standalone-config-bundle":
            include_companion_bundle = True
        elif arg == "--no-companion-bundle":
            include_companion_bundle = False
        elif arg == "--all":
            run_all = True
        elif arg == "--verbose":
            verbose = True
        elif arg.startswith("-"):
            raise UsageError("unknown option: {}".format(arg))
        else:
            targets.append(arg)
    return include_companion_bundle, run_all, verbose, targets


def print_targeting_help(verb, available_mods):
    warning("No mod targets provided")
    success("Use --all to {} all mods, or pass one or more mod names".format(verb))
    if available_mods:
        acronyms = mod_acronyms()
        success(
            "Available mods: {}".format(
                ", ".join(
                    "{} ({})".format(name, acronyms[name].lower()) if name in acronyms else name
                    for name in available_mods
                )
            )
        )
    else:
        warning("No mods found under mods/")


def resolve_mod_targets(run_all, requested_mods, verb):
    """Resolve the mod names to act on, or None when there is nothing to do.

    Prints targeting help / empty-state warnings as a side effect; callers
    return early on None. Raises when --all and explicit names are combined.
    """
    if run_all and requested_mods:
        raise RuntimeError("Use either --all or explicit mod names, not both")

    available_mods = discover_mods()
    if run_all:
        mod_names = available_mods
    elif requested_mods:
        mod_names = resolve_mod_names(requested_mods)
    else:
        print_targeting_help(verb, available_mods)
        return None

    if not mod_names:
        warning("No mods found under mods/")
        return None
    return mod_names


def ensure_mod_dirs_exist(mod_names):
    """Validate that each requested mod has a directory under mods/."""
    for mod_name in mod_names:
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            acronyms = mod_acronyms()
            known = ", ".join(
                "{} ({})".format(name, acronyms[name].lower()) if name in acronyms else name
                for name in discover_mods()
            )
            raise RuntimeError("Mod directory not found: {}. Available mods: {}".format(mod_dir, known))


def require_game_dir(env=None):
    """Return a validated WOT_GAME_DIR from the environment, or raise."""
    env = load_env() if env is None else env
    game_dir = env.get("WOT_GAME_DIR", "")
    if not game_dir:
        raise RuntimeError("WOT_GAME_DIR is not set. Create .env from .env.example and set it.")
    if not os.path.isdir(game_dir):
        raise RuntimeError("WOT_GAME_DIR does not exist: {}".format(game_dir))
    return game_dir


def run_entrypoint(main_impl):
    """Run a command's _main(), turning domain errors into a clean SystemExit.

    CompanionArtifactError and WotVersionError both subclass RuntimeError, so a
    single RuntimeError guard covers every command's failure mode.
    """
    try:
        return main_impl()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
