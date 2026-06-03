"""
Development/test cleanup helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Resolves the pinned WoT client version and verifies it matches <WOT_GAME_DIR>/version.xml.
3. Resolves mod ids from mods/<name>/meta.xml.
4. Removes deployed .wotmod files for each mod id from <WOT_GAME_DIR>/mods/<version>/.
5. Removes deployed config directories from <WOT_GAME_DIR>/mods/configs/<mod-name>/.

Usage:
    wot_mods_cleanup --all
    wot_mods_cleanup --dry-run
    wot_mods_cleanup research-progress-bar
    wot_mods_cleanup mod-a mod-b
    wot_mods_cleanup --verbose research-progress-bar
    python -m tools.cleanup research-progress-bar

Note:
    Cleanup requires WoT to be closed. The command exits if the client is running.
"""

from __future__ import annotations

import os
import shutil
import sys
import xml.etree.ElementTree as ET

from .console import detail, section, success, warning
from .paths import ENV_PATH, MODS_DIR
from .wot_process import ensure_wot_not_running
from .wot_version import resolve_target_wot_version


def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env

    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def read_meta(mod_name):
    meta_path = os.path.join(MODS_DIR, mod_name, "meta.xml")
    tree = ET.parse(meta_path)
    root = tree.getroot()
    return {
        "id": root.findtext("id", "").strip(),
        "version": root.findtext("version", "0.0.0.0").strip(),
        "wot_client_version": root.findtext("wot_client_version", "").strip(),
    }


def discover_mods():
    if not os.path.isdir(MODS_DIR):
        return []
    return sorted(d for d in os.listdir(MODS_DIR) if os.path.isdir(os.path.join(MODS_DIR, d)))


def parse_args(argv):
    dry_run = False
    run_all = False
    verbose = False
    targets = []
    for arg in argv:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--all":
            run_all = True
        elif arg == "--verbose":
            verbose = True
        else:
            targets.append(arg)
    return dry_run, run_all, verbose, targets


def _print_targeting_help(available_mods):
    warning("No mod targets provided")
    success("Use --all to clean all mods, or pass one or more mod names")
    if available_mods:
        success("Available mods: {}".format(", ".join(available_mods)))
    else:
        warning("No mods found under mods/")


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
    if meta.get("wot_client_version") != target_wot_version:
        raise RuntimeError(
            "meta.xml version mismatch for {}: meta.xml has {}, expected {} from WoT version pins".format(
                mod_name,
                meta.get("wot_client_version"),
                target_wot_version,
            )
        )

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
    if run_all and requested_mods:
        raise RuntimeError("Use either --all or explicit mod names, not both")

    available_mods = discover_mods()
    if run_all:
        mod_names = available_mods
    elif requested_mods:
        mod_names = requested_mods
    else:
        _print_targeting_help(available_mods)
        return

    if not mod_names:
        warning("No mods found under mods/")
        return

    ensure_wot_not_running("wot_mods_cleanup")

    env = load_env(ENV_PATH)
    game_dir = env.get("WOT_GAME_DIR", "")

    if not game_dir:
        raise RuntimeError("WOT_GAME_DIR is not set. Create .env from .env.example and set it.")
    if not os.path.isdir(game_dir):
        raise RuntimeError("WOT_GAME_DIR does not exist: {}".format(game_dir))
    target_wot_version = resolve_target_wot_version(env, require_game_dir=True)

    for mod_name in mod_names:
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            raise RuntimeError("Mod directory not found: {}".format(mod_dir))

    section("Cleanup")
    success("Target WoT mods version: {}".format(target_wot_version))

    removed_count = 0
    for mod_name in mod_names:
        if cleanup_mod(game_dir, mod_name, dry_run, target_wot_version, verbose=verbose):
            removed_count += 1

    mode = "DRY-RUN" if dry_run else "APPLIED"
    success("Cleanup {} for {} mod(s), changes in {}.".format(mode, len(mod_names), removed_count))


def main():
    try:
        return _main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
