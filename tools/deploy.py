"""
Development/test deployment helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Builds mods via wot_mods_build (all mods by default, or selected mods via args).
3. Detects installed WoT version folders under <WOT_GAME_DIR>/mods/.
4. Deploys each .wotmod to every detected <WOT_GAME_DIR>/mods/<version>/.
5. Deploys config files and optional i18n files to <WOT_GAME_DIR>/mods/configs/<mod-name>/.

Usage:
    wot_mods_deploy
    wot_mods_deploy research-progress-bar
    wot_mods_deploy --no-companion-bundle research-progress-bar
    python -m tools.deploy research-progress-bar

Note:
    Deployment updates files on disk only. A running WoT client will not hot-reload
    Python/UI/package changes from the copied .wotmod.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from .companion_artifacts import CompanionArtifactError, manifest_defines_bundle, resolve_cached_bundle_artifacts
from .companion_artifacts import load_manifest as load_companion_manifest
from .paths import DIST_DIR, ENV_PATH, MODS_DIR


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


def is_wot_running():
    try:
        result = subprocess.run(
            ["tasklist"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "").lower()
        names = [
            "worldoftanks",
            "worldoftanks64",
            "worldoftanks.exe",
            "worldoftanks64.exe",
        ]
        return any(name in output for name in names)
    except Exception:
        return False


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


def parse_version_key(name):
    parts = name.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def resolve_installed_mods_versions(game_dir):
    mods_root = os.path.join(game_dir, "mods")
    if not os.path.isdir(mods_root):
        raise RuntimeError("WoT mods directory not found: {}".format(mods_root))

    version_dirs = []
    for name in os.listdir(mods_root):
        version_key = parse_version_key(name)
        if version_key is None:
            continue

        version_path = os.path.join(mods_root, name)
        if os.path.isdir(version_path):
            version_dirs.append((version_key, name))

    if not version_dirs:
        raise RuntimeError("No WoT version folders found under {}".format(mods_root))

    version_dirs.sort(key=lambda item: item[0])
    return [name for _, name in version_dirs]


def build_mods(mod_names, include_companion_bundle=None):
    cmd = [sys.executable, "-m", "tools.build", *mod_names]
    if include_companion_bundle is False:
        cmd.insert(3, "--no-companion-bundle")
    elif include_companion_bundle:
        cmd.insert(3, "--standalone-config-bundle")
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


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
    flat_config_path = os.path.join(mod_dir, "config.json")
    legacy_config_dir = os.path.join(mod_dir, "config")

    has_flat_config = os.path.isfile(flat_config_path)
    has_legacy_config_dir = directory_has_entries(legacy_config_dir)

    if has_flat_config and has_legacy_config_dir:
        raise RuntimeError(
            "{} defines both config.json and config/; keep exactly one config source.".format(os.path.basename(mod_dir))
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


def deploy_mod(game_dir, mod_name, target_wot_version, include_companion_bundle=None):
    meta = read_meta(mod_name)
    mod_id = meta["id"]
    version = meta["version"]

    if not mod_id:
        raise RuntimeError("meta.xml for {} is missing id".format(mod_name))

    archive_name = "{}_{}.wotmod".format(mod_id, version)
    src_archive = os.path.join(DIST_DIR, archive_name)
    if not os.path.isfile(src_archive):
        raise RuntimeError("Built archive not found: {}".format(src_archive))

    dst_mods_dir = os.path.join(game_dir, "mods", target_wot_version)
    os.makedirs(dst_mods_dir, exist_ok=True)
    dst_archive = os.path.join(dst_mods_dir, archive_name)
    try:
        shutil.copy2(src_archive, dst_archive)
        print("Deployed package: {}".format(dst_archive))
    except PermissionError:
        print("SKIP package (in use): {}".format(dst_archive))

    if should_include_companion_bundle(mod_name, include_companion_bundle):
        for item in _resolve_deploy_companion_artifacts(mod_name):
            dst_path = os.path.join(dst_mods_dir, item["artifact"]["filename"])
            try:
                shutil.copy2(item["path"], dst_path)
                print("Deployed companion: {}".format(dst_path))
            except PermissionError:
                print("SKIP companion (in use): {}".format(dst_path))

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
        print("Deployed config:  {}".format(dst_config_dir))


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
    mod_names = []
    for arg in argv:
        if arg == "--standalone-config-bundle":
            include_companion_bundle = True
            continue
        if arg == "--no-companion-bundle":
            include_companion_bundle = False
            continue
        mod_names.append(arg)
    return include_companion_bundle, mod_names


def main():
    env = load_env(ENV_PATH)
    game_dir = env.get("WOT_GAME_DIR", "")

    if not game_dir:
        raise RuntimeError("WOT_GAME_DIR is not set. Create .env from .env.example and set it.")
    if not os.path.isdir(game_dir):
        raise RuntimeError("WOT_GAME_DIR does not exist: {}".format(game_dir))

    wot_running = is_wot_running()
    if wot_running:
        print(
            "WARNING: WoT appears to be running. Deployment will update files on disk,"
            " but the current client session will not hot-reload Python/UI/package changes."
        )

    include_companion_bundle, requested_mods = parse_args(sys.argv[1:])
    mod_names = requested_mods if requested_mods else discover_mods()
    if not mod_names:
        print("No mods found under mods/.")
        return

    # Validate requested mod directories before build.
    for mod_name in mod_names:
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            raise RuntimeError("Mod directory not found: {}".format(mod_dir))

    target_wot_versions = resolve_installed_mods_versions(game_dir)
    print("Target WoT mods versions: {}".format(", ".join(target_wot_versions)))

    build_mods(mod_names, include_companion_bundle=include_companion_bundle)

    for mod_name in mod_names:
        for target_wot_version in target_wot_versions:
            deploy_mod(
                game_dir,
                mod_name,
                target_wot_version,
                include_companion_bundle=include_companion_bundle,
            )

    print("Done. Development deployment finished for {} mod(s).".format(len(mod_names)))
    if wot_running:
        print("Next step: restart WoT to load the updated mod package.")
    else:
        print("Next step: launch WoT to load the updated mod package.")


if __name__ == "__main__":
    main()
