"""
Development/test deployment helper for WoT mods.

What it does:
1. Reads WOT_GAME_DIR from .env in repo root.
2. Builds mods via build.py (all mods by default, or selected mods via args).
3. Deploys each .wotmod to <WOT_GAME_DIR>/mods/<wot_client_version>/.
4. Deploys config files to <WOT_GAME_DIR>/mods/configs/<mod-name>/.

Usage:
    python dev_test_deploy.py
    python dev_test_deploy.py research-progress-bar
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODS_DIR = os.path.join(SCRIPT_DIR, 'mods')
DIST_DIR = os.path.join(SCRIPT_DIR, 'dist')
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


def build_mods(mod_names):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'build.py')] + list(mod_names)
    print('Running:', ' '.join(cmd))
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


def deploy_mod(game_dir, mod_name):
    meta = read_meta(mod_name)
    mod_id = meta['id']
    version = meta['version']
    wot_version = meta['wot_client_version']

    if not mod_id or not wot_version:
        raise RuntimeError(
            'meta.xml for {} is missing id or wot_client_version'.format(mod_name)
        )

    archive_name = '{}_{}.wotmod'.format(mod_id, version)
    src_archive = os.path.join(DIST_DIR, archive_name)
    if not os.path.isfile(src_archive):
        raise RuntimeError('Built archive not found: {}'.format(src_archive))

    dst_mods_dir = os.path.join(game_dir, 'mods', wot_version)
    os.makedirs(dst_mods_dir, exist_ok=True)
    dst_archive = os.path.join(dst_mods_dir, archive_name)
    try:
        shutil.copy2(src_archive, dst_archive)
        print('Deployed package: {}'.format(dst_archive))
    except PermissionError:
        print('SKIP package (in use): {}'.format(dst_archive))

    src_config_dir = os.path.join(MODS_DIR, mod_name, 'config')
    if os.path.isdir(src_config_dir):
        dst_config_dir = os.path.join(game_dir, 'mods', 'configs', mod_name)
        copy_tree_contents(src_config_dir, dst_config_dir)
        print('Deployed config:  {}'.format(dst_config_dir))


def main():
    env = load_env(ENV_PATH)
    game_dir = env.get('WOT_GAME_DIR', '')

    if not game_dir:
        raise RuntimeError(
            'WOT_GAME_DIR is not set. Create .env from .env.example and set it.'
        )
    if not os.path.isdir(game_dir):
        raise RuntimeError('WOT_GAME_DIR does not exist: {}'.format(game_dir))

    requested_mods = sys.argv[1:]
    mod_names = requested_mods if requested_mods else discover_mods()
    if not mod_names:
        print('No mods found under mods/.')
        return

    # Validate requested mod directories before build.
    for mod_name in mod_names:
        mod_dir = os.path.join(MODS_DIR, mod_name)
        if not os.path.isdir(mod_dir):
            raise RuntimeError('Mod directory not found: {}'.format(mod_dir))

    build_mods(mod_names)

    for mod_name in mod_names:
        deploy_mod(game_dir, mod_name)

    print('Done. Development deployment finished for {} mod(s).'.format(len(mod_names)))


if __name__ == '__main__':
    main()
