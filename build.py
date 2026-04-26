"""
build.py — packages mods under mods/<name>/ into .wotmod archives.

Usage:
    python build.py                        # build all mods under mods/
    python build.py research-progress-bar  # build one specific mod

Output: dist/<mod-id>_<version>.wotmod

Internal .wotmod layout:
    meta.xml
    res/scripts/client/gui/mods/<file>.py   (from mods/<name>/src/)
    res/...                                 (from mods/<name>/res/)

Config files are NOT bundled.
Ship them separately to: <WoT install>/mods/configs/<mod-folder-name>/

Note: the template/ directory is a scaffold for new mods — it is not built here.
Copy it to mods/<new-mod-name>/ to start a new mod.
"""

import os
import sys
import zipfile
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODS_DIR = os.path.join(SCRIPT_DIR, 'mods')
DIST_DIR = os.path.join(SCRIPT_DIR, 'dist')


def read_meta(mod_dir):
    meta_path = os.path.join(mod_dir, 'meta.xml')
    tree = ET.parse(meta_path)
    root = tree.getroot()
    return {
        'id': root.findtext('id', '').strip(),
        'version': root.findtext('version', '0.0.0.0').strip(),
    }


def build_mod(mod_name):
    mod_dir = os.path.join(MODS_DIR, mod_name)
    if not os.path.isdir(mod_dir):
        print('ERROR: mod directory not found: {}'.format(mod_dir))
        return False

    meta = read_meta(mod_dir)
    mod_id = meta['id']
    version = meta['version']

    if not mod_id or 'yourname' in mod_id:
        print('WARNING: {} — mod id looks like a placeholder: {}'.format(mod_name, mod_id))

    output_name = '{}_{}.wotmod'.format(mod_id, version)
    os.makedirs(DIST_DIR, exist_ok=True)
    output_path = os.path.join(DIST_DIR, output_name)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # meta.xml at archive root
        zf.write(os.path.join(mod_dir, 'meta.xml'), 'meta.xml')

        # src/*.py  →  res/scripts/client/gui/mods/<file>.py
        src_dir = os.path.join(mod_dir, 'src')
        if os.path.isdir(src_dir):
            for filename in sorted(os.listdir(src_dir)):
                if filename.endswith('.py'):
                    abs_path = os.path.join(src_dir, filename)
                    archive_path = 'res/scripts/client/gui/mods/{}'.format(filename)
                    zf.write(abs_path, archive_path)

        # res/ tree  →  res/ inside the archive
        res_dir = os.path.join(mod_dir, 'res')
        if os.path.isdir(res_dir):
            for dirpath, _, filenames in os.walk(res_dir):
                for filename in sorted(filenames):
                    abs_path = os.path.join(dirpath, filename)
                    archive_path = os.path.relpath(abs_path, mod_dir).replace(os.sep, '/')
                    zf.write(abs_path, archive_path)

    print('Built: {}'.format(output_path))

    config_dir = os.path.join(mod_dir, 'config')
    if os.path.isdir(config_dir):
        print('  Config (ship separately):')
        print('    Source: {}'.format(config_dir))
        print('    Deploy to: <WoT install>/mods/configs/{}/'.format(mod_name))

    return True


def main():
    targets = sys.argv[1:]

    if targets:
        for mod_name in targets:
            build_mod(mod_name)
    else:
        if not os.path.isdir(MODS_DIR):
            print('No mods/ directory found.')
            return
        mod_names = sorted(
            d for d in os.listdir(MODS_DIR)
            if os.path.isdir(os.path.join(MODS_DIR, d))
        )
        if not mod_names:
            print('No mods found under mods/.')
            return
        for mod_name in mod_names:
            build_mod(mod_name)


if __name__ == '__main__':
    main()
