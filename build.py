"""
build.py — packages mods under mods/<name>/ into .wotmod archives.

Usage:
    python build.py                        # build all mods under mods/
    python build.py research-progress-bar  # build one specific mod

Output: dist/<mod-id>_<version>.wotmod

Optional prebuild hooks:
- If mods/<name>/ui/compile_ui.py exists, it is run before packaging that mod.
- Generated packaged assets should land under mods/<name>/ui/build/res/.
- build.py stages both mods/<name>/res/ and generated ui/build/res/ into the final archive.

Internal .wotmod layout:
    meta.xml
    res/scripts/client/gui/mods/<file>.pyc  (compiled from mods/<name>/src/)
    res/...                                 (from mods/<name>/res/ plus generated ui/build/res/)

Additional release output:
    dist/<mod-id>_<version>/README.txt
    dist/<mod-id>_<version>/mods/<wot_client_version>/<mod-id>_<version>.wotmod
    dist/<mod-id>_<version>/mods/configs/<mod-folder-name>/...

Config files are NOT bundled.
Ship them separately to: <WoT install>/mods/configs/<mod-folder-name>/

Optional authored source layout:
    mods/<name>/config.json                →  mods/configs/<mod-folder-name>/config.json
    mods/<name>/i18n/*.yml                 →  res/mods/<meta.id>/text/*.yml
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
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


def compile_py2_to_pyc(py2_exe, src_path, out_pyc_path):
    # WoT runtime for this client/mod stack expects Python 2 bytecode.
    cmd = [
        py2_exe,
        '-c',
        'import py_compile,sys; py_compile.compile(sys.argv[1], sys.argv[2])',
        src_path,
        out_pyc_path,
    ]
    subprocess.check_call(cmd)


def run_optional_prebuild(mod_dir):
    hook_path = os.path.join(mod_dir, 'ui', 'compile_ui.py')
    if not os.path.isfile(hook_path):
        return

    cmd = [sys.executable, hook_path]
    print('Running: {}'.format(' '.join(cmd)))
    subprocess.check_call(cmd)


def read_meta(mod_dir):
    meta_path = os.path.join(mod_dir, 'meta.xml')
    tree = ET.parse(meta_path)
    root = tree.getroot()
    return {
        'id': root.findtext('id', '').strip(),
        'version': root.findtext('version', '0.0.0.0').strip(),
        'wot_client_version': root.findtext('wot_client_version', '').strip(),
    }


def copy_tree_contents(src_dir, dst_dir):
    if not os.path.isdir(src_dir):
        return

    os.makedirs(dst_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        src_path = os.path.join(src_dir, name)
        dst_path = os.path.join(dst_dir, name)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            dst_parent = os.path.dirname(dst_path)
            if dst_parent:
                os.makedirs(dst_parent, exist_ok=True)
            shutil.copy2(src_path, dst_path)


def copy_file(src_path, dst_path):
    dst_parent = os.path.dirname(dst_path)
    if dst_parent:
        os.makedirs(dst_parent, exist_ok=True)
    shutil.copy2(src_path, dst_path)


def directory_has_entries(path):
    return os.path.isdir(path) and bool(os.listdir(path))


def resolve_config_source(mod_dir):
    flat_config_path = os.path.join(mod_dir, 'config.json')
    legacy_config_dir = os.path.join(mod_dir, 'config')

    has_flat_config = os.path.isfile(flat_config_path)
    has_legacy_config_dir = directory_has_entries(legacy_config_dir)

    if has_flat_config and has_legacy_config_dir:
        raise RuntimeError(
            '{} defines both config.json and config/; keep exactly one config source.'.format(
                os.path.basename(mod_dir)
            )
        )
    if has_flat_config:
        return 'file', flat_config_path
    if has_legacy_config_dir:
        return 'dir', legacy_config_dir
    return None


def stage_i18n_resources(mod_dir, mod_id, staged_res_dir):
    i18n_dir = os.path.join(mod_dir, 'i18n')
    if not os.path.isdir(i18n_dir):
        return

    legacy_text_dir = os.path.join(mod_dir, 'res', 'mods', mod_id, 'text')
    if directory_has_entries(legacy_text_dir):
        raise RuntimeError(
            '{} defines both i18n/ and res/mods/{}/text/; keep exactly one localisation source.'.format(
                os.path.basename(mod_dir),
                mod_id,
            )
        )

    copy_tree_contents(i18n_dir, os.path.join(staged_res_dir, 'mods', mod_id, 'text'))


def stage_resource_trees(mod_dir, mod_id, staged_res_dir):
    copy_tree_contents(os.path.join(mod_dir, 'res'), staged_res_dir)
    stage_i18n_resources(mod_dir, mod_id, staged_res_dir)
    copy_tree_contents(os.path.join(mod_dir, 'ui', 'build', 'res'), staged_res_dir)


def copy_config_source(mod_dir, dst_config_dir):
    config_source = resolve_config_source(mod_dir)
    if not config_source:
        return None

    source_kind, source_path = config_source
    if source_kind == 'dir':
        copy_tree_contents(source_path, dst_config_dir)
    else:
        copy_file(source_path, os.path.join(dst_config_dir, 'config.json'))
    return source_path


def write_release_readme(readme_path, archive_name, mod_name, wot_client_version):
    lines = [
        'World of Tanks mod release bundle',
        '',
        'Contents:',
        '  - mods/{0}/{1}'.format(wot_client_version, archive_name),
        '  - mods/configs/{0}/'.format(mod_name),
        '',
        'Installation:',
        '  1. Close World of Tanks.',
        '  2. Copy the included mods/ folder into your World of Tanks game directory.',
        '  3. Merge/overwrite files when prompted.',
        '  4. Launch the game and verify the mod in python.log if needed.',
        '',
        'Notes:',
        '  - The .wotmod package belongs under mods/{0}/.'.format(wot_client_version),
        '  - The config folder belongs under mods/configs/{0}/.'.format(mod_name),
    ]
    with open(readme_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


def create_release_bundle(mod_dir, mod_name, meta, output_path):
    archive_name = os.path.basename(output_path)
    bundle_name = os.path.splitext(archive_name)[0]
    bundle_root = os.path.join(DIST_DIR, bundle_name)
    wot_client_version = meta.get('wot_client_version') or 'UNKNOWN_GAME_VERSION'

    if os.path.isdir(bundle_root):
        shutil.rmtree(bundle_root)

    package_dir = os.path.join(bundle_root, 'mods', wot_client_version)
    os.makedirs(package_dir, exist_ok=True)
    shutil.copy2(output_path, os.path.join(package_dir, archive_name))

    config_source_path = copy_config_source(
        mod_dir,
        os.path.join(bundle_root, 'mods', 'configs', mod_name),
    )
    if config_source_path:
        bundle_config_dir = os.path.join(bundle_root, 'mods', 'configs', mod_name)

    write_release_readme(
        os.path.join(bundle_root, 'README.txt'),
        archive_name,
        mod_name,
        wot_client_version,
    )
    return bundle_root


def iter_python_source_files(src_dir):
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = sorted(
            name for name in dirnames
            if name != '__pycache__'
        )
        for filename in sorted(filenames):
            if not filename.endswith('.py'):
                continue
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, src_dir)
            yield abs_path, rel_path


def build_mod(mod_name, py2_exe):
    mod_dir = os.path.join(MODS_DIR, mod_name)
    if not os.path.isdir(mod_dir):
        print('ERROR: mod directory not found: {}'.format(mod_dir))
        return False

    run_optional_prebuild(mod_dir)

    meta = read_meta(mod_dir)
    mod_id = meta['id']
    version = meta['version']

    if not mod_id or 'yourname' in mod_id:
        print('WARNING: {} — mod id looks like a placeholder: {}'.format(mod_name, mod_id))

    output_name = '{}_{}.wotmod'.format(mod_id, version)
    os.makedirs(DIST_DIR, exist_ok=True)
    output_path = os.path.join(DIST_DIR, output_name)

    with tempfile.TemporaryDirectory(prefix='wot-build-') as temp_dir:
        # WoT's package loader rejects compressed entries in some client versions.
        # Use store-only zip members for maximum compatibility.
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zf:
            # meta.xml at archive root
            zf.write(os.path.join(mod_dir, 'meta.xml'), 'meta.xml')

            # src/**/*.py  →  res/scripts/client/gui/mods/<relative-path>.pyc
            src_dir = os.path.join(mod_dir, 'src')
            if os.path.isdir(src_dir):
                for abs_path, rel_path in iter_python_source_files(src_dir):
                    compiled_rel_path = '{}c'.format(rel_path)
                    compiled_path = os.path.join(temp_dir, compiled_rel_path)
                    compiled_dir = os.path.dirname(compiled_path)
                    if compiled_dir:
                        os.makedirs(compiled_dir, exist_ok=True)
                    compile_py2_to_pyc(py2_exe, abs_path, compiled_path)
                    archive_path = 'res/scripts/client/gui/mods/{}'.format(
                        compiled_rel_path.replace(os.sep, '/')
                    )
                    zf.write(compiled_path, archive_path)

            # Stage packaged resources from committed source plus generated build output.
            staged_res_dir = os.path.join(temp_dir, 'staged_res')
            stage_resource_trees(mod_dir, mod_id, staged_res_dir)
            if os.path.isdir(staged_res_dir):
                for dirpath, dirnames, filenames in os.walk(staged_res_dir):
                    dirnames[:] = sorted(dirnames)
                    for filename in sorted(filenames):
                        abs_path = os.path.join(dirpath, filename)
                        archive_path = 'res/{}'.format(
                            os.path.relpath(abs_path, staged_res_dir).replace(os.sep, '/')
                        )
                        zf.write(abs_path, archive_path)

    print('Built: {}'.format(output_path))

    release_bundle_dir = create_release_bundle(mod_dir, mod_name, meta, output_path)
    print('  Release bundle: {}'.format(release_bundle_dir))

    config_source = resolve_config_source(mod_dir)
    if config_source:
        _, config_source_path = config_source
        print('  Config (ship separately):')
        print('    Source: {}'.format(config_source_path))
        print('    Deploy to: <WoT install>/mods/configs/{}/'.format(mod_name))

    return True


def main():
    env = load_env(ENV_PATH)
    py2_exe = env.get('WOT_PYTHON2_EXE', '').strip()
    if not py2_exe:
        raise RuntimeError('WOT_PYTHON2_EXE is required in .env for this repository.')
    if not os.path.isfile(py2_exe):
        raise RuntimeError('WOT_PYTHON2_EXE does not exist: {}'.format(py2_exe))
    targets = sys.argv[1:]

    if targets:
        for mod_name in targets:
            build_mod(mod_name, py2_exe)
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
            build_mod(mod_name, py2_exe)


if __name__ == '__main__':
    main()
