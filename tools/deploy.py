"""
Development/test deployment helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Resolves the pinned WoT client version and verifies it matches <WOT_GAME_DIR>/version.xml.
3. Deploys each .wotmod from dist/ to <WOT_GAME_DIR>/mods/<version>/.
4. Deploys config files and optional i18n files to <WOT_GAME_DIR>/mods/configs/<mod-name>/.

Usage:
    wot_mods_deploy --all
    wot_mods_deploy research-progress-bar
    wot_mods_deploy mod-a mod-b
    wot_mods_deploy --no-companion-bundle research-progress-bar
    wot_mods_deploy --verbose research-progress-bar
    python -m tools.deploy research-progress-bar

Note:
    Deployment copies pre-built artifacts from dist/ — run wot_mods_build first.
    Close WoT before deploying (no automatic running-process check; in-use files are skipped).
"""

from __future__ import annotations

import os
import shutil
import sys

from .companion_artifacts import CompanionArtifactError, manifest_defines_bundle, resolve_cached_bundle_artifacts
from .companion_artifacts import load_manifest as load_companion_manifest
from .console import detail, section, success, warning
from .env import load_env
from .mod_meta import read_meta
from .paths import DIST_DIR, MODS_DIR
from .wot_version import resolve_target_wot_version


def discover_mods():
    if not os.path.isdir(MODS_DIR):
        return []
    return sorted(d for d in os.listdir(MODS_DIR) if os.path.isdir(os.path.join(MODS_DIR, d)))


def copy_tree_contents(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for name in os.listdir(src_dir):
        src_path = os.path.join(src_dir, name)
        dst_path = os.path.join(dst_dir, name)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dst_path)


def copy_file(src_path, dst_path):
    dst_parent = os.path.dirname(dst_path)
    if dst_parent:
        os.makedirs(dst_parent, exist_ok=True)
    shutil.copy2(src_path, dst_path)


def directory_has_entries(path):
    return os.path.isdir(path) and bool(os.listdir(path))


def resolve_config_source(mod_dir):
    flat_config_path = os.path.join(mod_dir, "config.template.json")
    legacy_config_dir = os.path.join(mod_dir, "config")

    has_flat_config = os.path.isfile(flat_config_path)
    has_legacy_config_dir = directory_has_entries(legacy_config_dir)

    if has_flat_config and has_legacy_config_dir:
        raise RuntimeError(
            "{} defines both config.template.json and config/; keep exactly one config source.".format(
                os.path.basename(mod_dir)
            )
        )
    if has_flat_config:
        return "file", flat_config_path
    if has_legacy_config_dir:
        return "dir", legacy_config_dir
    return None


def resolve_i18n_source(mod_dir):
    i18n_dir = os.path.join(mod_dir, "i18n")
    if directory_has_entries(i18n_dir):
        return i18n_dir
    return None


def deploy_mod(game_dir, mod_name, target_wot_version, include_companion_bundle=None, verbose=False):
    meta = read_meta(mod_name)
    mod_id = meta["id"]
    version = meta["version"]

    if not mod_id:
        raise RuntimeError("meta.xml for {} is missing id".format(mod_name))

    archive_name = "{}_{}.wotmod".format(mod_id, version)
    bundle_name = "{}_{}".format(mod_id, version)
    src_archive = os.path.join(DIST_DIR, bundle_name, "mods", target_wot_version, archive_name)
    if not os.path.isfile(src_archive):
        raise RuntimeError("Built archive not found: {}".format(src_archive))

    dst_mods_dir = os.path.join(game_dir, "mods", target_wot_version)
    os.makedirs(dst_mods_dir, exist_ok=True)
    dst_archive = os.path.join(dst_mods_dir, archive_name)
    try:
        shutil.copy2(src_archive, dst_archive)
        success("Package deployed to mods/{}".format(target_wot_version))
        detail("Path: {}".format(dst_archive), verbose=verbose)
    except PermissionError:
        warning("SKIP package (in use): {}".format(dst_archive))

    if should_include_companion_bundle(mod_name, include_companion_bundle):
        deployed_companions = 0
        for item in _resolve_deploy_companion_artifacts(mod_name):
            dst_path = os.path.join(dst_mods_dir, item["artifact"]["filename"])
            try:
                shutil.copy2(item["path"], dst_path)
                deployed_companions += 1
                detail("Companion: {}".format(dst_path), verbose=verbose)
            except PermissionError:
                warning("SKIP companion (in use): {}".format(dst_path))
        if deployed_companions:
            success("Companions deployed: {}".format(deployed_companions))

    mod_dir = os.path.join(MODS_DIR, mod_name)
    dst_config_dir = os.path.join(game_dir, "mods", "configs", mod_name)

    config_source = resolve_config_source(mod_dir)
    if config_source:
        source_kind, source_path = config_source
        if source_kind == "dir":
            copy_tree_contents(source_path, dst_config_dir)
        else:
            copy_file(source_path, os.path.join(dst_config_dir, "config.json"))

    i18n_source = resolve_i18n_source(mod_dir)
    if i18n_source:
        copy_tree_contents(i18n_source, os.path.join(dst_config_dir, "i18n"))

    if config_source or i18n_source:
        success("Config deployed")
        detail("Path: {}".format(dst_config_dir), verbose=verbose)


def _resolve_deploy_companion_artifacts(mod_name):
    manifest = load_companion_manifest()
    if mod_name not in (manifest.get("bundles") or {}):
        return []

    try:
        return resolve_cached_bundle_artifacts(mod_name, manifest=manifest)
    except CompanionArtifactError as exc:
        raise RuntimeError(str(exc)) from exc


def should_include_companion_bundle(mod_name, include_companion_bundle):
    if include_companion_bundle is not None:
        return include_companion_bundle
    try:
        return manifest_defines_bundle(mod_name)
    except CompanionArtifactError as exc:
        raise RuntimeError(str(exc)) from exc


def parse_args(argv):
    include_companion_bundle = None
    run_all = False
    verbose = False
    mod_names = []
    for arg in argv:
        if arg == "--standalone-config-bundle":
            include_companion_bundle = True
            continue
        if arg == "--no-companion-bundle":
            include_companion_bundle = False
            continue
        if arg == "--all":
            run_all = True
            continue
        if arg == "--verbose":
            verbose = True
            continue
        mod_names.append(arg)
    return include_companion_bundle, run_all, verbose, mod_names


def _print_targeting_help(available_mods):
    warning("No mod targets provided")
    success("Use --all to deploy all mods, or pass one or more mod names")
    if available_mods:
        success("Available mods: {}".format(", ".join(available_mods)))
    else:
        warning("No mods found under mods/")


def _main():
    include_companion_bundle, run_all, verbose, requested_mods = parse_args(sys.argv[1:])
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

    env = load_env()
    game_dir = env.get("WOT_GAME_DIR", "")

    if not game_dir:
        raise RuntimeError("WOT_GAME_DIR is not set. Create .env from .env.example and set it.")
    if not os.path.isdir(game_dir):
        raise RuntimeError("WOT_GAME_DIR does not exist: {}".format(game_dir))
    target_wot_version = resolve_target_wot_version(env, require_game_dir=True)

    # Validate requested mod directories before deploying.
    for mod_name in mod_names:
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            raise RuntimeError("Mod directory not found: {}".format(mod_dir))

    section("Preparing deployment")
    success("Target WoT mods version: {}".format(target_wot_version))

    for mod_name in mod_names:
        section("Deploying {}".format(mod_name))
        detail("Target version: {}".format(target_wot_version), verbose=verbose)
        deploy_mod(
            game_dir,
            mod_name,
            target_wot_version,
            include_companion_bundle=include_companion_bundle,
            verbose=verbose,
        )

    section("Deployment complete")
    success("Development deployment finished for {} mod(s)".format(len(mod_names)))
    success("Next step: launch WoT to load the updated mod package")


def main():
    try:
        return _main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
