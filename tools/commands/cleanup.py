"""
Development/test cleanup helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Resolves the pinned WoT client version and verifies it matches <WOT_GAME_DIR>/version.xml.
3. Resolves mod ids from mods/<name>/meta.xml.
4. Removes deployed .wotmod files for each mod id from <WOT_GAME_DIR>/mods/<version>/.
5. Removes deployed config directories from <WOT_GAME_DIR>/mods/configs/<mod-name>/.

Usage:
    zwm cleanup --all
    zwm cleanup --dry-run
    zwm cleanup research-progress-bar
    zwm cleanup mod-a mod-b
    zwm cleanup --verbose research-progress-bar
    python -m tools.commands.cleanup research-progress-bar

Note:
    Close WoT before cleanup (no automatic running-process check; in-use files are skipped).
"""

from __future__ import annotations

import os
import shutil
import sys

from ..core.console import detail, section, success, warning
from ..core.env import load_env
from ..core.mod_meta import read_meta
from ..core.modcli import (
    ensure_mod_dirs_exist,
    require_game_dir,
    resolve_mod_targets,
    run_entrypoint,
    split_targeting_args,
)
from ..core.wot_version import resolve_target_wot_version


def parse_args(argv):
    flags, targets = split_targeting_args(argv, {"--dry-run": "dry_run", "--all": "run_all", "--verbose": "verbose"})
    return flags["dry_run"], flags["run_all"], flags["verbose"], targets


def remove_path(path, dry_run, verbose=False):
    if not os.path.exists(path):
        return False

    if dry_run:
        detail("DRY-RUN remove: {}".format(path), verbose=True)
        return True

    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        detail("Removed: {}".format(path), verbose=verbose)
        return True
    except PermissionError:
        warning("SKIP (in use): {}".format(path))
        return False


def _iter_deployed_package_paths(game_dir, target_wot_version, mod_id):
    packages_dir = os.path.join(game_dir, "mods", target_wot_version)
    if not os.path.isdir(packages_dir):
        return []

    package_prefix = "{}_".format(mod_id)
    package_suffix = ".wotmod"
    paths = []
    for entry in os.listdir(packages_dir):
        if not entry.startswith(package_prefix) or not entry.endswith(package_suffix):
            continue
        paths.append(os.path.join(packages_dir, entry))
    return sorted(paths)


def cleanup_mod(game_dir, mod_name, dry_run, target_wot_version, verbose=False):
    meta = read_meta(mod_name)
    mod_id = meta["id"]

    if not mod_id:
        raise RuntimeError("meta.xml for {} is missing id".format(mod_name))

    package_paths = _iter_deployed_package_paths(game_dir, target_wot_version, mod_id)
    config_dir = os.path.join(game_dir, "mods", "configs", mod_name)

    removed_any = False
    for package_path in package_paths:
        removed_any |= remove_path(package_path, dry_run, verbose=verbose)
    removed_any |= remove_path(config_dir, dry_run, verbose=verbose)

    if removed_any:
        success("Cleaned {}".format(mod_name))
    else:
        detail("Nothing to remove for mod: {}".format(mod_name), verbose=verbose)

    return removed_any


def _main():
    dry_run, run_all, verbose, requested_mods = parse_args(sys.argv[1:])
    mod_names = resolve_mod_targets(run_all, requested_mods, "clean")
    if mod_names is None:
        return

    env = load_env()
    game_dir = require_game_dir(env)
    target_wot_version = resolve_target_wot_version(env, require_game_dir=True)

    ensure_mod_dirs_exist(mod_names)

    section("Cleanup")
    success("Target WoT mods version: {}".format(target_wot_version))

    removed_count = 0
    for mod_name in mod_names:
        if cleanup_mod(game_dir, mod_name, dry_run, target_wot_version, verbose=verbose):
            removed_count += 1

    mode = "DRY-RUN" if dry_run else "APPLIED"
    success("Cleanup {} for {} mod(s), changes in {}.".format(mode, len(mod_names), removed_count))


def main():
    return run_entrypoint(_main)


if __name__ == "__main__":
    main()
