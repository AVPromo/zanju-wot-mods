"""
Development/test cleanup helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Resolves mod package names from mods/<name>/meta.xml.
3. Detects the newest installed WoT version folder under <WOT_GAME_DIR>/mods/.
4. Removes deployed .wotmod files from <WOT_GAME_DIR>/mods/<latest_version>/.
5. Removes deployed config directories from <WOT_GAME_DIR>/mods/configs/<mod-name>/.

Usage:
    python dev_test_cleanup.py
    python dev_test_cleanup.py --dry-run
    python dev_test_cleanup.py research-progress-bar
"""

from __future__ import annotations

import os
import shutil
import sys
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODS_DIR = os.path.join(SCRIPT_DIR, 'mods')
ENV_PATH = os.path.join(SCRIPT_DIR, '.env')


def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env

    with open(path, 'r', encoding='utf-8') as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def read_meta(mod_name):
    meta_path = os.path.join(MODS_DIR, mod_name, 'meta.xml')
    tree = ET.parse(meta_path)
    root = tree.getroot()
    return {
        'id': root.findtext('id', '').strip(),
        'version': root.findtext('version', '0.0.0.0').strip(),
        'wot_client_version': root.findtext('wot_client_version', '').strip(),
    }


def discover_mods():
    if not os.path.isdir(MODS_DIR):
        return []
    return sorted(
        d
        for d in os.listdir(MODS_DIR)
        if os.path.isdir(os.path.join(MODS_DIR, d))
    )


def parse_version_key(name):
    parts = name.split('.')
    if not parts or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def resolve_latest_mods_version(game_dir):
    mods_root = os.path.join(game_dir, 'mods')
    if not os.path.isdir(mods_root):
        raise RuntimeError('WoT mods directory not found: {}'.format(mods_root))

    version_dirs = []
    for name in os.listdir(mods_root):
        version_key = parse_version_key(name)
        if version_key is None:
            continue

        version_path = os.path.join(mods_root, name)
        if os.path.isdir(version_path):
            version_dirs.append((version_key, name))

    if not version_dirs:
        raise RuntimeError(
            'No WoT version folders found under {}'.format(mods_root)
        )

    return max(version_dirs, key=lambda item: item[0])[1]


def parse_args(argv):
    dry_run = False
    targets = []
    for arg in argv:
        if arg == '--dry-run':
            dry_run = True
        else:
            targets.append(arg)
    return dry_run, targets


def remove_path(path, dry_run):
    if not os.path.exists(path):
        return False

    if dry_run:
        print('DRY-RUN remove: {}'.format(path))
        return True

    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        print('Removed: {}'.format(path))
        return True
    except PermissionError:
        print('SKIP (in use): {}'.format(path))
        return False


def cleanup_mod(game_dir, mod_name, dry_run, target_wot_version):
    meta = read_meta(mod_name)
    mod_id = meta['id']
    version = meta['version']

    if not mod_id:
        raise RuntimeError('meta.xml for {} is missing id'.format(mod_name))

    package_name = '{}_{}.wotmod'.format(mod_id, version)
    package_path = os.path.join(game_dir, 'mods', target_wot_version, package_name)
    config_dir = os.path.join(game_dir, 'mods', 'configs', mod_name)

    removed_any = False
    removed_any |= remove_path(package_path, dry_run)
    removed_any |= remove_path(config_dir, dry_run)

    if not removed_any:
        print('Nothing to remove for mod: {}'.format(mod_name))


def main():
    dry_run, requested_mods = parse_args(sys.argv[1:])

    env = load_env(ENV_PATH)
    game_dir = env.get('WOT_GAME_DIR', '')

    if not game_dir:
        raise RuntimeError(
            'WOT_GAME_DIR is not set. Create .env from .env.example and set it.'
        )
    if not os.path.isdir(game_dir):
        raise RuntimeError('WOT_GAME_DIR does not exist: {}'.format(game_dir))

    mod_names = requested_mods if requested_mods else discover_mods()
    if not mod_names:
        print('No mods found under mods/.')
        return

    for mod_name in mod_names:
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            raise RuntimeError('Mod directory not found: {}'.format(mod_dir))

    target_wot_version = resolve_latest_mods_version(game_dir)
    print('Target WoT mods version: {}'.format(target_wot_version))

    for mod_name in mod_names:
        cleanup_mod(game_dir, mod_name, dry_run, target_wot_version)

    mode = 'DRY-RUN' if dry_run else 'APPLIED'
    print('Cleanup {} for {} mod(s).'.format(mode, len(mod_names)))


if __name__ == '__main__':
    main()
