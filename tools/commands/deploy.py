"""
Development/test deployment helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Resolves the pinned WoT client version and verifies it matches <WOT_GAME_DIR>/version.xml.
3. Deploys each .wotmod from dist/ to <WOT_GAME_DIR>/mods/<version>/.
4. Deploys i18n files to <WOT_GAME_DIR>/mods/configs/<mod-name>/i18n/.

Usage:
    zwm deploy --all
    zwm deploy research-progress-bar
    zwm deploy mod-a mod-b
    zwm deploy --no-companion-bundle research-progress-bar
    zwm deploy --verbose research-progress-bar
    python -m tools.commands.deploy research-progress-bar

Note:
    Deployment copies pre-built artifacts from dist/ — run zwm build first.
    Close WoT before deploying (no automatic running-process check; in-use files are skipped).
"""

from __future__ import annotations

import os
import shutil
import sys

from ..core.companion_artifacts import resolve_bundle_artifacts_if_defined, should_include_companion_bundle
from ..core.console import detail, section, success, warning
from ..core.env import load_env
from ..core.mod_assets import stage_i18n_source
from ..core.mod_cli import (
    ensure_mod_dirs_exist,
    parse_companion_targeting_args,
    require_game_dir,
    resolve_mod_targets,
    run_entrypoint,
)
from ..core.mod_meta import read_meta
from ..core.paths import DIST_DIR, MODS_DIR
from ..core.wot_version import resolve_target_wot_version


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
        for item in resolve_bundle_artifacts_if_defined(mod_name):
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

    i18n_source = stage_i18n_source(mod_dir, os.path.join(dst_config_dir, "i18n"))

    if i18n_source:
        success("i18n deployed")
        detail("Path: {}".format(os.path.join(dst_config_dir, "i18n")), verbose=verbose)


def _main():
    include_companion_bundle, run_all, verbose, requested_mods = parse_companion_targeting_args(sys.argv[1:])
    mod_names = resolve_mod_targets(run_all, requested_mods, "deploy")
    if mod_names is None:
        return

    env = load_env()
    game_dir = require_game_dir(env)
    target_wot_version = resolve_target_wot_version(env, require_game_dir=True)

    # Validate requested mod directories before deploying.
    ensure_mod_dirs_exist(mod_names)

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
    return run_entrypoint(_main)


if __name__ == "__main__":
    main()
